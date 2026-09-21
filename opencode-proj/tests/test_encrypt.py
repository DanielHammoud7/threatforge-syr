"""توثيق الأدلة — اختبارات الحلقة الآمنة: roundtrip، تلاعب، عبارة خاطئة (M4 معيار النجاح)."""
import base64
import json

import config
import pytest

from features.evidence import encrypt

PW = "sup3r-secret-12345"
PDF = b"%PDF-1.4 fake report body " * 40
IMAGE = b"\x89PNG\r\n\x1a\n fake image bytes " * 10


@pytest.fixture()
def case_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "STORAGE_DIR", tmp_path)
    analysis = {"score": 82, "band_en": "critical"}
    legal = {"refs": ["المادة 20"], "labels": ["الابتزاز والتهديد الإلكتروني"]}
    cid = encrypt.new_case_id()
    path = encrypt.persist_case(
        case_id=cid, pdf_bytes=PDF, image_bytes=IMAGE, image_name="shot.png",
        analysis=analysis, legal=legal, passphrase=PW,
    )
    return path


def test_case_writes_full_bundle(case_dir):
    assert (case_dir / "report.pdf").read_bytes() == PDF
    encoded = json.loads((case_dir / "report.enc").read_text(encoding="utf-8"))
    assert encoded["ciphertext_b64"]
    manifest = json.loads((case_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["sha256_report"] == encrypt.sha256_bytes(PDF)
    assert manifest["sha256_original_image"] == encrypt.sha256_bytes(IMAGE)
    assert manifest["risk"]["score"] == 82
    assert (case_dir / "original.png").exists()


def test_roundtrip_decrypt_matches_original(case_dir):
    assert encrypt.decrypt_case(case_dir, PW) == PDF


def test_wrong_passphrase_fails_authentication(case_dir):
    with pytest.raises(encrypt.InvalidAuthenticationError):
        encrypt.decrypt_case(case_dir, "wrong-passphrase-123")


def test_tampered_pdf_breaks_digest_but_bundle_stays_valid(case_dir):
    # report.pdf نسخة مساعدة للعرض؛ الحزمة الحجّة هي report.enc وفق مثبت في manifest
    pdf_path = case_dir / "report.pdf"
    pdf_path.write_bytes(PDF[:-1] + b"X")
    verify = encrypt.verify_integrity(case_dir)
    assert verify["all_ok"] is False
    assert verify["pdf_integrity_ok"] is False
    assert encrypt.decrypt_case(case_dir, PW) == PDF


def test_tampered_ciphertext_breaks_authentication(case_dir):
    enc_path = case_dir / "report.enc"
    payload = json.loads(enc_path.read_text(encoding="utf-8"))
    ct = bytearray(base64.b64decode(payload["ciphertext_b64"]))
    ct[-1] ^= 0x01
    payload["ciphertext_b64"] = base64.b64encode(bytes(ct)).decode("ascii")
    enc_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(encrypt.InvalidAuthenticationError):
        encrypt.decrypt_case(case_dir, PW)


def test_tampered_manifest_breaks_auth_via_aad(case_dir):
    manifest_path = case_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["sha256_report"] = "0" * 64
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(encrypt.InvalidAuthenticationError):
        encrypt.decrypt_case(case_dir, PW)


def test_verify_integrity_true_on_untouched(case_dir):
    assert encrypt.verify_integrity(case_dir)["all_ok"] is True


def test_sha256_is_deterministic():
    assert encrypt.sha256_bytes(b"a") == encrypt.sha256_bytes(b"a")
    assert encrypt.sha256_bytes(b"a") != encrypt.sha256_bytes(b"b")


def test_new_case_id_is_incrementing_and_prefixed(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "STORAGE_DIR", tmp_path)
    c1 = encrypt.new_case_id()
    date = c1.split("-")[1]
    (tmp_path / date / c1).mkdir(parents=True)  # محاكاة حفظ حالة c1
    c2 = encrypt.new_case_id()
    assert c1.startswith("SYR-")
    assert c1 != c2


def test_short_passphrase_rejected():
    with pytest.raises(ValueError):
        encrypt.derive_key("short", b"salt" * 4)