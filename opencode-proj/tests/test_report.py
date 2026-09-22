"""توليد تقرير PDF — معيار النجاح: ملف صالح، يحتوي مقاطع الأقسام الأربعة (M3)."""
import io

import pytest
from PIL import Image as PILImage

from features.analysis import redflags
from features.evidence import encrypt
from features.legal import mapping
from features.report import generate
from tests.test_redflags import THREAT_EXTORTION, BENIGN_1

FONT_PRESENT = any(f.exists() for f in generate.FONT_CANDIDATES)


@pytest.fixture()
def report_bytes():
    if not FONT_PRESENT:
        pytest.skip("لا يوجد خط TTF يدعم العربية في هذا النظام")
    analysis = redflags.analyze(THREAT_EXTORTION)
    legal = mapping.legal_qualification(analysis)
    data = generate.ReportData(
        case_id="SYR-TEST-0001",
        created_utc="2026-09-21T12:00:00+00:00",
        analysis=analysis,
        legal=legal,
        original_text=THREAT_EXTORTION,
        ocr_text="",
        image_bytes=_tiny_png(),
        image_name="screenshot.png",
        sha256_report="",
    )
    pdf = generate.build_pdf(data)
    data.sha256_report = encrypt.sha256_bytes(pdf)
    return pdf


def _tiny_png() -> bytes:
    buf = io.BytesIO()
    PILImage.new("RGB", (320, 120), "white").save(buf, format="PNG")
    return buf.getvalue()


def test_pdf_header_and_size(report_bytes):
    assert report_bytes[:5] == b"%PDF-"
    assert len(report_bytes) > 3000


def test_report_with_image_is_larger():
    if not FONT_PRESENT:
        pytest.skip("لا يوجد خط TTF يدعم العربية في هذا النظام")
    base = _build(BENIGN_1, image_bytes=None)
    with_img = _build(BENIGN_1, image_bytes=_tiny_png())
    assert len(with_img) > len(base) + 200


def _build(text, image_bytes, image_name=None):
    analysis = redflags.analyze(text)
    legal = mapping.legal_qualification(analysis)
    if image_bytes is not None and image_name is None:
        image_name = "screenshot.png"
    data = generate.ReportData(
        case_id="SYR-TEST-0003", created_utc="2026-09-21T12:00:00+00:00",
        analysis=analysis, legal=legal, original_text=text, ocr_text="",
        image_bytes=image_bytes, image_name=image_name, sha256_report="",
    )
    return generate.build_pdf(data)


def test_benign_report_still_builds():
    if not FONT_PRESENT:
        pytest.skip("لا يوجد خط TTF يدعم العربية في هذا النظام")
    analysis = redflags.analyze(BENIGN_1)
    legal = mapping.legal_qualification(analysis)
    data = generate.ReportData(
        case_id="SYR-TEST-0002", created_utc="2026-09-21T12:00:00+00:00",
        analysis=analysis, legal=legal, original_text=BENIGN_1, ocr_text="",
        image_bytes=None, image_name=None, sha256_report="",
    )
    pdf = generate.build_pdf(data)
    assert pdf[:5] == b"%PDF-"


def test_arabic_shaping_util():
    assert generate.ar("مرحبا بالعالم") != ""


# ── حصانة SRE (Regression): لا انهيار أبداً عند غياب خطوط النظام بفضل الخط المضمّن ──
def _bundled_font():
    bundled = next(f for f in generate.FONT_CANDIDATES if f.name.startswith("NotoNaskhArabic"))
    assert bundled.exists(), "الخط المضمّن data/fonts/NotoNaskhArabic-Regular.ttf مفقود!"
    return bundled


def test_resolve_font_uses_bundled_when_no_system_fonts(monkeypatch):
    # بيئة مثل حاوية Streamlit Cloud بلا خطوط نظام: مرشّح واحد فقط — الخط المضمّن
    monkeypatch.setattr(generate, "FONT_CANDIDATES", [_bundled_font()])
    assert generate._resolve_font() == _bundled_font()


def test_build_pdf_succeeds_with_only_bundled_font(monkeypatch):
    monkeypatch.setattr(generate, "FONT_CANDIDATES", [_bundled_font()])
    analysis = redflags.analyze(THREAT_EXTORTION)
    legal = mapping.legal_qualification(analysis)
    data = generate.ReportData(
        case_id="SYR-FONT-0001", created_utc="2026-09-22T00:00:00+00:00",
        analysis=analysis, legal=legal, original_text=THREAT_EXTORTION, ocr_text="",
        image_bytes=None, image_name=None, sha256_report="",
    )
    pdf = generate.build_pdf(data)
    assert pdf[:5] == b"%PDF-"
    assert len(pdf) > 3000