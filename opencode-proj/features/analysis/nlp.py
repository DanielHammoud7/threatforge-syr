"""معالجة لغوية عربية خفيفة — تعتمد فقط على nltk.RegexpTokenizer (بلا تنزيل بيانات).

التطبيع: إزالة التشكيل/التطويل، توحيد الهمزات (أ/إ/آ→ا) والتاء المربوطة (ة→ه) والياء
(ى→ي)، إزالة علامات الاتجاه (bidi marks)، ضغط الفراغات. القواعد في redflags.toml
تُصاغ على الأشكال المطبّعة بعد هذا التطبيع.
"""
from __future__ import annotations

import re
from collections import Counter
from functools import lru_cache

from nltk.tokenize import RegexpTokenizer

from config import DATA_DIR

_DIACRITICS = re.compile(r"[\u064B-\u0652\u0670]")
_TATWEEL = re.compile(r"\u0640+")
_BIDI_MARKS = re.compile(r"[\u200b\u200c\u200d\u200e\u200f\u061c\u2066-\u2069]")
_WS = re.compile(r"\s+")
_HAMZA_MAP = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ة": "ه", "ى": "ي"})
_SENT_SPLIT = re.compile(r"(?<=[.!؟?])\s+")
_TOKENIZER = RegexpTokenizer(r"[\w\u0600-\u06FF]+")


def normalize(text: str) -> str:
    """تطبيع النص العربي للقواعد (نمط واحد للكشف)."""
    t = _DIACRITICS.sub("", text)
    t = _TATWEEL.sub("", t)
    t = _BIDI_MARKS.sub("", t)
    t = t.translate(_HAMZA_MAP)
    t = _WS.sub(" ", t)
    return t.strip()


def sentences(text: str) -> list[str]:
    """تقسيم إلى جمل على علامات الترقيم العربية، بعد التطبيع."""
    return [s for s in _SENT_SPLIT.split(normalize(text)) if s]


def raw_sentences(text: str) -> list[str]:
    """تقسيم النص الخام (للعرض) — نفس الحدود دون تطبيع."""
    cleaned = text.replace("\u200f", "").replace("\u200e", "").replace("\u061c", "")
    return [s.strip() for s in _SENT_SPLIT.split(cleaned) if s.strip()]


@lru_cache(maxsize=1)
def _stopwords() -> set[str]:
    path = DATA_DIR / "arabic_stopwords.txt"
    words = path.read_text(encoding="utf-8").splitlines()
    return {normalize(w) for w in words if w.strip()}


def tokenize(text: str) -> list[str]:
    """تقسيم إلى رموز وإزالة الكلمات الوظيفية العربية."""
    stop = _stopwords()
    return [t for t in _TOKENIZER.tokenize(normalize(text)) if t not in stop]


def top_keywords(text: str, limit: int = 8) -> list[str]:
    """أكثر الكلمات المفتاحية تكراراً (للميتاداتا التفسيرية)."""
    return [w for w, _ in Counter(tokenize(text)).most_common(limit)]