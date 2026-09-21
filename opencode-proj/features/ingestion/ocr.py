"""الادخال (نص / صورة) واستخراج النصوص من لقطات الشاشة (OCR عربي + إنجليزي).

pytesseract غلاف لثنائي Tesseract الخارجي؛ تُتفحص المسارات الشائعة تلقائياً
ويُدار الغياب كخطأ إجرائي واضح (لا فشل صامت).
"""
from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path

import cv2
import numpy as np
import pytesseract

from config import ALLOWED_IMAGE_EXT, OCR_LANGS, OCR_PSM, TESSDATA_DIR, TESSERACT_CANDIDATES

log = logging.getLogger(__name__)


class OCRUnavailableError(RuntimeError):
    """ثنائي Tesseract أو حزم اللغات غير متوفرة."""


class ImageDecodeError(ValueError):
    """الصورة تالفة أو بصيغة غير مدعومة."""


_ENV_PROBED = False


def _probe_tesseract() -> None:
    """اكتشاف ثنائي Tesseract مرة واحدة (مسار افتراضي/مشترك/مشروع vendor)."""
    global _ENV_PROBED
    if _ENV_PROBED:
        return
    _ENV_PROBED = True
    if TESSDATA_DIR.exists() and not os.environ.get("TESSDATA_PREFIX"):
        os.environ["TESSDATA_PREFIX"] = str(TESSDATA_DIR)
    try:
        pytesseract.get_tesseract_version()
        return
    except pytesseract.TesseractNotFoundError:
        pass
    for candidate in TESSERACT_CANDIDATES:
        if candidate.exists():
            pytesseract.pytesseract.tesseract_cmd = str(candidate)
            return
    found = shutil.which("tesseract")
    if found:
        pytesseract.pytesseract.tesseract_cmd = found


def is_allowed_image(name: str) -> bool:
    return Path(name).suffix.lower() in ALLOWED_IMAGE_EXT


def extract_text_from_image(image_bytes: bytes) -> str:
    """يستخرج النص من صورة لقطة شاشة.

    يرمي ImageDecodeError لصورة غير مقروءة وOCRUnavailableError عند غياب المحرك/اللغات.
    """
    _probe_tesseract()
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ImageDecodeError(
            "تعذر فك تشفير الصورة — تأكد أنها ملف PNG/JPG سليم وغير تالف."
        )
    processed = _preprocess(img)
    try:
        text = pytesseract.image_to_string(processed, lang=OCR_LANGS, config=f"--psm {OCR_PSM}")
    except pytesseract.TesseractNotFoundError as exc:
        raise OCRUnavailableError(
            "محرك Tesseract غير مثبت على النظام. ثبّت Tesseract 5.5 (حزمة UB-Mannheim على ويندوز) "
            "وثبّت حزمتي اللغة ara وeng (انظر README / PROJECT_MAP [ORPHANS & PENDING])."
        ) from exc
    except pytesseract.TesseractError as exc:
        raise OCRUnavailableError(
            f"خطأ في محرك Tesseract (غالباً حزمتا اللغتين ara/eng غير مثبتتين): {exc}"
        ) from exc
    if not text or not text.strip():
        raise ImageDecodeError(
            "لم يُستخرج أي نص من الصورة — الصورة قد تكون فارغة أو الإضاءة/الوضوح غير كافيين."
        )
    log.info("OCR مستخرج بنجاح: %d حرفاً", len(text))
    return text.strip()


def _preprocess(img: np.ndarray) -> np.ndarray:
    """معالجة مسبقة تحسينية: تدرج رمادي، تكبير، تعتيم، عتبة Otsu."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    _, th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return th