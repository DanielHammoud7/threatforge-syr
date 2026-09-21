"""مولّد التقرير الجنائي PDF — محتوى عربي RTL (arabic-reshaper + python-bidi) عبر ReportLab.

التقرير يضم: ترويسة القضية، نتائج التحليل (شريط خطورة + فئات + اقتباسات)، النص الخام
والمستخرج، الصورة الأصلية، التوصيف القانوني، وبصمات السلامة (SHA-256).
"""
from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from arabic_reshaper import reshape
from bidi.algorithm import get_display
from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.shapes import Drawing, Rect
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from config import APP_NAME, APP_VERSION, FONT_CANDIDATES, PDF_PAGE_CM

log = logging.getLogger(__name__)

_BAND_COLORS = {"low": colors.HexColor("#2e7d32"), "medium": colors.HexColor("#f9a825"),
                "high": colors.HexColor("#ef6c00"), "critical": colors.HexColor("#c62828")}
_DISCLAIMER = (
    "إخلاء مسؤولية: هذا التقرير أداة توثيق وتحليل تقنية استرشادية؛ التوصيف القانوني وأرقام "
    "المواد تُراجع مقابل النص الرسمي لقانون الجريمة المعلوماتية رقم 20 لعام 2022 من جهة مختصة "
    "قبل التقديم القضائي. حُسّبت بصمات SHA-256 عند لحظة التوثيق؛ الصلاحية تستند إلى حفظ البصمة "
    "والملف المشفر دون تعديل."
)


@dataclass
class ReportData:
    case_id: str
    created_utc: str
    analysis: dict
    legal: dict
    original_text: str
    ocr_text: str
    image_bytes: bytes | None
    image_name: str | None
    sha256_report: str


def ar(text: str) -> str:
    """تشكيل عربي + إعادة ترتيب الاتجاه (Bidi) قبل العرض في PDF."""
    return get_display(reshape(str(text)))


def _resolve_font() -> Path:
    for candidate in FONT_CANDIDATES:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        "لم يُعثر على خط TTF يدعم العربية — أضف مسار خطاً صالحاً إلى FONT_CANDIDATES في config.py"
    )


def _styles() -> dict[str, ParagraphStyle]:
    base = ParagraphStyle(
        "base", fontName="ArFont", fontSize=10, leading=15,
        alignment=TA_RIGHT, textColor=colors.HexColor("#222222"), wordWrap="RTL",
    )
    title = ParagraphStyle("title", parent=base, fontSize=17, leading=22, alignment=TA_CENTER,
                           textColor=colors.HexColor("#0d2f52"))
    h2 = ParagraphStyle("h2", parent=base, fontSize=12.5, leading=17,
                        textColor=colors.HexColor("#0d2f52"), spaceBefore=10)
    small = ParagraphStyle("small", parent=base, fontSize=8.5, leading=12,
                           textColor=colors.HexColor("#666666"))
    return {"base": base, "title": title, "h2": h2, "small": small}


def build_pdf(data: ReportData) -> bytes:
    buf = io.BytesIO()
    font_path = _resolve_font()
    pdfmetrics.registerFont(TTFont("ArFont", str(font_path)))

    doc = SimpleDocTemplate(
        buf, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm,
        topMargin=15 * mm, bottomMargin=18 * mm,
        title=f"تقرير أدلة — {data.case_id}", author=APP_NAME,
    )
    styles = _styles()
    story: list = []

    # ── الترويسة
    story.append(Paragraph(ar(f"{APP_NAME} — تقرير توثيق الأدلة"), styles["title"]))
    story.append(Paragraph(ar(f"رقم الحالة: {data.case_id}"), styles["base"]))
    story.append(Paragraph(f"UTC: {data.created_utc} · وثّق في: {data.legal.get('documented_at','')}", styles["base"]))
    story.append(Spacer(1, 6))

    # ── نتائج التحليل
    a = data.analysis
    story.append(Paragraph(ar("1) نتائج تحليل الخطر"), styles["h2"]))
    story.append(Paragraph(
        ar(f"مؤشر الخطورة: {a['score']}/100 — النطاق: {a['band_ar']} ({a['band_en']})") +
        " · " + (" | ".join(a["flags"]) if a["flags"] else ar("لا مؤشرات سلوكية ظاهرة")),
        styles["base"],
    ))
    story.append(_score_bar(a["score"], a["band_en"]))
    for cat in a["categories"]:
        story.append(Paragraph(
            ar(f"◼ {cat['label']} — درجة الفئة: {cat['subscore']}"),
            ParagraphStyle("cat", parent=styles["base"], textColor=colors.HexColor("#0d2f52"), spaceBefore=4),
        ))
        for hit in cat["hits"]:
            story.append(Paragraph(ar(f"— «{hit['quote']}»"), styles["small"]))
    if a.get("keywords"):
        story.append(Paragraph(ar(f"كلمات مفتاحية: {', '.join(a['keywords'])}"), styles["small"]))

    # ── النصوص
    story.append(Paragraph(ar("2) نص الأدلة"), styles["h2"]))
    if data.ocr_text:
        story.append(Paragraph(ar(f"النص المستخرج عبر OCR (ara+eng):\n{data.ocr_text}"), styles["base"]))
    if data.original_text and data.original_text != data.ocr_text:
        story.append(Paragraph(ar(f"النص المُدخل مباشرة:\n{data.original_text}"), styles["base"]))
    if data.image_bytes and data.image_name:
        story.append(Spacer(1, 4))
        story.append(_image_flowable(data.image_bytes, data.image_name))

    # ── التوصيف القانوني
    story.append(Paragraph(ar("3) التوصيف القانوني (استرشادي)"), styles["h2"]))
    story.append(Paragraph(ar(f"المرجع: {data.legal.get('law', '')}"), styles["base"]))
    story.append(Paragraph(
        ar("المواد ذات الصلة: " + ("، ".join(data.legal["refs"]) if data.legal["refs"] else "—")), styles["base"]))
    for para in data.legal["narrative"].split("\n\n"):
        story.append(Paragraph(ar(para), styles["base"]))

    # ── السلامة والبصمات
    story.append(Paragraph(ar("4) بصمات السلامة الرقمية"), styles["h2"]))
    digest_lines = [f"SHA-256 (report.pdf): {data.sha256_report}",
                    f"AES-256-GCM مفتاح مشتق PBKDF2-HMAC-SHA256 ({600_000} تكراراً)"]
    story.append(Paragraph(ar("\n".join(digest_lines)), styles["base"]))

    def _footer(canvas, _doc_):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.grey)
        canvas.drawString(16 * mm, 10 * mm, f"{APP_NAME} v{APP_VERSION} — {data.case_id}")
        canvas.drawRightString(194 * mm, 10 * mm, f"صفحة {canvas.getPageNumber()}")
        canvas.restoreState()

    def _disclaimer(canvas, _doc_):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.grey)
        _wrap(canvas, _DISCLAIMER, 16 * mm, 13 * mm, 178 * mm)
        canvas.restoreState()

    doc.build(story, onFirstPage=_disclaimer, onLaterPages=_footer)
    return buf.getvalue()


def _wrap(canvas, text: str, x: float, y: float, width: float) -> None:
    """رسم إخلاء المسؤولية ملفوفاً في تذييل الصفحة الأولى (أبجدي إنجليزي آمن)."""
    from reportlab.pdfbase.pdfmetrics import stringWidth
    lines, current = [], ""
    for word in text.split():
        trial = f"{current} {word}".strip()
        if stringWidth(trial, "Helvetica", 7) <= width:
            current = trial
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    for i, line in enumerate(lines):
        canvas.drawString(x, y - i * 9, line)


def _score_bar(score: int, band_en: str) -> Drawing:
    w, h = 160, 12
    draw = Drawing(w, h + 2)
    draw.add(Rect(0, 0, w, h, fillColor=colors.HexColor("#e0e0e0")))
    fill = max(4, int(w * score / 100))
    draw.add(Rect(0, 0, fill, h, fillColor=_BAND_COLORS.get(band_en, colors.grey)))
    return draw


def _image_flowable(image_bytes: bytes, image_name: str) -> Image:
    try:
        with PILImage.open(io.BytesIO(image_bytes)) as im:
            w_px, h_px = im.size
    except Exception:
        w_px, h_px = (1200, 800)
    max_w, max_h = 170 * mm, 120 * mm
    ratio = min(max_w / w_px, max_h / h_px, 1.0)
    return Image(io.BytesIO(image_bytes), width=int(w_px * ratio), height=int(h_px * ratio))


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")