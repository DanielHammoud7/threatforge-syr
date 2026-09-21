"""تكامل E2E: لقطة شاشة عربية حقيقية → OCR → تحليل → PDF → تشفير → تحقق (M5 معيار النجاح)."""
import io
import re

import pytest
from PIL import Image, ImageDraw, ImageFont
from arabic_reshaper import reshape
from bidi.algorithm import get_display

import config
from config import FONT_CANDIDATES
from features.analysis import redflags
from features.evidence import encrypt
from features.ingestion import ocr
from features.legal import mapping
from features.report import generate


def _render_arabic(text: str) -> bytes:
    font_path = next((f for f in FONT_CANDIDATES if f.exists()), None)
    if font_path is None:
        pytest.skip("لا يوجد خط TTF لدعم العربية")
    img = Image.new("RGB", (1100, 200), "white")
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(str(font_path), 46)
    draw.text((30, 55), get_display(reshape(text)), fill="black", font=font)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture()
def readiness():
    try:
        ocr._probe_tesseract()
        ocr.pytesseract.get_tesseract_version()
    except Exception:
        pytest.skip("ثنائي Tesseract غير متوفر")
    if not any(f.exists() for f in FONT_CANDIDATES):
        pytest.skip("لا يوجد خط TTF يدعم العربية")
    return True


def test_full_journey_with_ocr_image(readiness, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "STORAGE_DIR", tmp_path)

    # 1) صورة لقطة شاشة محتواها تهديد
    image_bytes = _render_arabic("إذا لم تدفع المبلغ سأنشر صورك على المنصة")

    # 2) OCR
    text = ocr.extract_text_from_image(image_bytes)
    assert re.search(r"[\u0600-\u06FF]{3,}", text), text

    # 3) تحليل
    analysis = redflags.analyze(text)
    assert analysis["score"] >= 40, analysis

    # 4) توصيف قانوني + تقرير
    legal = mapping.legal_qualification(analysis)
    assert legal["refs"]
    report_data = generate.ReportData(
        case_id="SYR-E2E-0001",
        created_utc=generate.utc_now_iso(),
        analysis=analysis, legal=legal,
        original_text="", ocr_text=text,
        image_bytes=image_bytes, image_name="screenshot.png",
        sha256_report="",
    )
    pdf = generate.build_pdf(report_data)
    assert pdf[:5] == b"%PDF-"
    report_data.sha256_report = encrypt.sha256_bytes(pdf)

    # 5) تشفير وحفظ
    case_id = encrypt.new_case_id()
    case_dir = encrypt.persist_case(
        case_id=case_id, pdf_bytes=pdf, image_bytes=image_bytes,
        image_name="screenshot.png", analysis=analysis, legal=legal,
        passphrase="e2e-secret-pass-42",
    )

    # 6) تحقق كامل
    assert encrypt.verify_integrity(case_dir)["all_ok"] is True
    assert encrypt.decrypt_case(case_dir, "e2e-secret-pass-42") == pdf
    with pytest.raises(encrypt.InvalidAuthenticationError):
        encrypt.decrypt_case(case_dir, "wrong-passphrase")