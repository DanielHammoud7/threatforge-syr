"""OCR — يختبر استخراج النص العربي من صورة لقطة شاشة (يتطلب ثنائي Tesseract خارجياً)."""
import io
import re

import pytest
from PIL import Image, ImageDraw, ImageFont
from arabic_reshaper import reshape
from bidi.algorithm import get_display

from config import FONT_CANDIDATES
from features.ingestion import ocr


def _render_arabic(text: str) -> bytes:
    font_path = next((f for f in FONT_CANDIDATES if f.exists()), None)
    if font_path is None:
        pytest.skip("لا يوجد خط TTF لدعم العربية")
    img = Image.new("RGB", (900, 160), "white")
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(str(font_path), 42)
    draw.text((30, 45), get_display(reshape(text)), fill="black", font=font)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _tesseract_ready() -> bool:
    try:
        ocr._probe_tesseract()
        ocr.pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


@pytest.fixture()
def ready():
    if not _tesseract_ready():
        pytest.skip("ثنائي Tesseract غير متوفر في هذه البيئة — اختبار OCR معلّق")
    return True


def test_extract_arabic_text_from_screenshot(ready):
    text = ocr.extract_text_from_image(_render_arabic("إذا لم تدفع سأنشر الصور"))
    assert re.search(r"[\u0600-\u06FF]{3,}", text), f"لم يُستخرج نص عربي: {text!r}"


def test_ocr_returns_non_empty_for_clear_shot(ready):
    text = ocr.extract_text_from_image(_render_arabic("مرحبا بك"))
    assert len(text) >= 3


def test_corrupt_image_raises_decode_error(ready):
    with pytest.raises(ocr.ImageDecodeError):
        ocr.extract_text_from_image(b"not-an-image-data")