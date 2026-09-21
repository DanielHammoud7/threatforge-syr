"""توثيق الأدلة وتشفيرها — SHA-256 digest + AES-256-GCM (مفتاح مشتق PBKDF2-HMAC-SHA256).

التصميم (قرار ADR-3/4 المعتمد): المفتاح يُشتق عند الطلب من عبارة سرية المستخدم ولا يُخزَّن
أبداً؛ البصمة SHA-256 مستقلة عن المفتاح؛ يُقيَّد النص المشفر (AAD) بالبصمة ورقم الحالة —
أي تعديل بايت واحد في التقرير أو البصمة أو الملف المشفر يُفشل المصادقة (InvalidTag).
"""
from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import config
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from config import (
    AES_KEY_BYTES,
    CASE_ID_DATE_FORMAT,
    CASE_ID_PREFIX,
    CIPHER_NAME,
    KDF_ALGORITHM,
    KDF_ITERATIONS,
    MIN_PASSPHRASE_LEN,
    NONCE_BYTES,
    SALT_BYTES,
)

log = logging.getLogger(__name__)


class InvalidAuthenticationError(Exception):
    """فشلت مصادقة البيانات المشفرة (عبارة سرية خاطئة أو ملف معدَّل)."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def new_case_id() -> str:
    """رقم حالة تسلسلي حتمي داخل اليوم: SYR-YYYYMMDD-NNNN."""
    now = datetime.now(timezone.utc)
    date_dir = config.STORAGE_DIR / now.strftime(CASE_ID_DATE_FORMAT)
    date_dir.mkdir(parents=True, exist_ok=True)
    seq = sum(1 for p in date_dir.iterdir() if p.is_dir()) + 1
    return f"{CASE_ID_PREFIX}-{now.strftime(CASE_ID_DATE_FORMAT)}-{seq:04d}"


def derive_key(passphrase: str, salt: bytes) -> bytes:
    if len(passphrase) < MIN_PASSPHRASE_LEN:
        raise ValueError(f"العبارة السرية يجب أن لا تقل عن {MIN_PASSPHRASE_LEN} محارف.")
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(), length=AES_KEY_BYTES, salt=salt, iterations=KDF_ITERATIONS
    )
    return kdf.derive(passphrase.encode("utf-8"))


def encrypt_bytes(data: bytes, passphrase: str, aad: bytes) -> dict:
    """تشفير بأمان: salt+nonce عشوائيان؛ AAD يربط بالميتاداتا (البصمة/رقم الحالة)."""
    salt = os.urandom(SALT_BYTES)
    nonce = os.urandom(NONCE_BYTES)
    key = derive_key(passphrase, salt)
    ciphertext = AESGCM(key).encrypt(nonce, data, aad)
    return {
        "ciphertext_b64": base64.b64encode(ciphertext).decode("ascii"),
        "nonce_b64": base64.b64encode(nonce).decode("ascii"),
        "salt_b64": base64.b64encode(salt).decode("ascii"),
        "aad_sha256": sha256_bytes(aad),
    }


def decrypt_payload(payload: dict, passphrase: str, aad: bytes) -> bytes:
    """فك التشفير مع التحقق (InvalidTag → InvalidAuthenticationError)."""
    key = derive_key(passphrase, base64.b64decode(payload["salt_b64"]))
    try:
        return AESGCM(key).decrypt(
            base64.b64decode(payload["nonce_b64"]),
            base64.b64decode(payload["ciphertext_b64"]),
            aad,
        )
    except InvalidTag as exc:
        raise InvalidAuthenticationError(
            "فشل التحقق من مصادقة البيانات: العبارة السرية خاطئة أو الملفات معدّلة."
        ) from exc


def persist_case(
    *,
    case_id: str,
    pdf_bytes: bytes,
    image_bytes: bytes | None,
    image_name: str | None,
    analysis: dict,
    legal: dict,
    passphrase: str,
) -> Path:
    """يحفظ حزمة الأدلة (report.pdf + report.enc + manifest.json + الصورة الأصلية).

    يرجع مسار مجلد الحالة. يعيد الاستخدام لرقم الحالة نفسه خطأ ValueError (منع الالتباس).
    """
    case_dir = config.STORAGE_DIR / case_id
    if case_dir.exists():
        raise ValueError(f"حالة موجودة مسبقاً: {case_id}")
    case_dir.mkdir(parents=True)

    created_utc = datetime.now(timezone.utc).isoformat(timespec="seconds")
    sha_pdf = sha256_bytes(pdf_bytes)
    sha_img = sha256_bytes(image_bytes) if image_bytes else None
    aad = f"TF:{case_id}:{sha_pdf}".encode("ascii")
    encrypted = encrypt_bytes(pdf_bytes, passphrase, aad)

    manifest = {
        "case_id": case_id,
        "created_utc": created_utc,
        "cipher": CIPHER_NAME,
        "kdf": KDF_ALGORITHM,
        "kdf_iterations": KDF_ITERATIONS,
        "nonce_b64": encrypted["nonce_b64"],
        "salt_b64": encrypted["salt_b64"],
        "aad_sha256": encrypted["aad_sha256"],
        "sha256_report": sha_pdf,
        "sha256_original_image": sha_img,
        "risk": {"score": analysis["score"], "band": analysis["band_en"]},
        "legal_refs": legal.get("refs", []),
        "matched_offenses": legal.get("labels", []),
    }
    (case_dir / "report.pdf").write_bytes(pdf_bytes)
    (case_dir / "report.enc").write_text(
        json.dumps(encrypted, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (case_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if image_bytes and image_name:
        suffix = Path(image_name).suffix or ".png"
        (case_dir / f"original{suffix}").write_bytes(image_bytes)
    log.info("حزمة أدلة محفوظة: %s (sha256=%s)", case_id, sha_pdf[:16])
    return case_dir


def decrypt_case(case_dir: Path, passphrase: str) -> bytes:
    """يفك حزمة حالة كاملة ويعيد بايتات report.pdf (يتحقق AAD بالبصمة)."""
    manifest = json.loads((case_dir / "manifest.json").read_text(encoding="utf-8"))
    payload = json.loads((case_dir / "report.enc").read_text(encoding="utf-8"))
    aad = f"TF:{manifest['case_id']}:{manifest['sha256_report']}".encode("ascii")
    if payload["aad_sha256"] != sha256_bytes(aad):
        raise InvalidAuthenticationError("تعارض AAD مع البصمة المسجلة — ملفات معدّلة.")
    return decrypt_payload(payload, passphrase, aad)


def verify_integrity(case_dir: Path) -> dict:
    """تحقق لا يحتاج عبارة سرية: تطابق بصمات report.pdf والصورة الأصلية مع manifest."""
    manifest = json.loads((case_dir / "manifest.json").read_text(encoding="utf-8"))
    pdf_ok = sha256_file(case_dir / "report.pdf") == manifest["sha256_report"]
    img_ok = True
    if manifest.get("sha256_original_image"):
        originals = list(case_dir.glob("original.*"))
        img_ok = bool(originals) and sha256_file(originals[0]) == manifest["sha256_original_image"]
    return {
        "pdf_integrity_ok": pdf_ok,
        "image_integrity_ok": img_ok,
        "all_ok": pdf_ok and img_ok,
        "manifest_risk": manifest["risk"],
        "manifest_created_utc": manifest["created_utc"],
    }