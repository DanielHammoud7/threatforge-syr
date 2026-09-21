"""ThreatForge SYR — مركز إعدادات التطبيق (مصدر الحقيقة الوحيد للثوابت).

لا تُعدَّل الثوابت التشغيلية إلا من هنا؛ تغيير الحزم عبر requirements.txt يمر
بمراجعة جدول [TECH_STACK] في PROJECT_MAP.md.
"""
from __future__ import annotations

from pathlib import Path

APP_NAME = "ThreatForge SYR"
APP_VERSION = "1.0.0"
APP_TAGLINE = "كشف التهديدات الرقمية وتوثيق الأدلة الجنائية"

# مسارات العمل (نسبية لجذر المشروع دوماً)
ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
STORAGE_DIR = ROOT / "storage" / "evidence"
LOGS_DIR = ROOT / "logs"
VENDOR_DIR = ROOT / "vendor"
TESSDATA_DIR = DATA_DIR / "tessdata"

# ── الادخال والـ OCR ──────────────────────────────────────────────
OCR_LANGS = "ara+eng"
OCR_PSM = 6
MAX_IMAGE_MB = 15
ALLOWED_IMAGE_EXT = {".png", ".jpg", ".jpeg"}
TESSERACT_CANDIDATES = [
    Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
    Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
]

# ── التحليل ونطاقات الخطر ──────────────────────────────────────────
RISK_BANDS = [
    ("منخفض", "low", 0, 24),
    ("متوسط", "medium", 25, 49),
    ("مرتفع", "high", 50, 74),
    ("حرج", "critical", 75, 100),
]
EARLY_WARNING_MIN_SCORE = 75
MAX_QUOTES_PER_CATEGORY = 5

# ── التشفير والأدلة ────────────────────────────────────────────────
CASE_ID_PREFIX = "SYR"
CASE_ID_DATE_FORMAT = "%Y%m%d"
KDF_ITERATIONS = 600_000
KDF_ALGORITHM = "pbkdf2_hmac_sha256"
CIPHER_NAME = "AES-256-GCM"
AES_KEY_BYTES = 32
SALT_BYTES = 16
NONCE_BYTES = 12
MIN_PASSPHRASE_LEN = 8

# ── التقرير ─────────────────────────────────────────────────────────
FONT_CANDIDATES = [
    Path(r"C:\Windows\Fonts\arial.ttf"),
    Path(r"C:\Windows\Fonts\Segoe UI.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
]
PDF_PAGE_CM = (21.0, 29.7)  # A4