"""محرك كشف مؤشرات الخطر — قواعد حتمية موزونة قابلة للتفسير والاستشهاد.

المنهجية: لكل فئة (ابتزاز/تهديد/احتيال/خصوصية) جدول أنماط regex مُحمّل من
data/redflags.toml؛ تُطابق على الجمل بعد التطبيع (nlp.normalize).
الدرجة الخام الفئوية = وزن الفئة × مجموع (boost × تطابق)، والإجمالي يقصّ عند 100.
النواتج موثقة الاقتباس (quote) ليتمكن المختص من تتبع كل نمط في المادة الخام.
"""
from __future__ import annotations

import logging
import re
import tomllib
from functools import lru_cache

from config import DATA_DIR, EARLY_WARNING_MIN_SCORE, MAX_QUOTES_PER_CATEGORY, RISK_BANDS
from . import nlp

log = logging.getLogger(__name__)

_FLAG_MONEY = re.compile(r"(دولار|ليره|الف|مليون|مبلغ|دفع|تحويل|حواله|فلوس|اموال)")
_FLAG_PUBLISH = re.compile(r"(بنشر|سانشر|نشر|بفضحك|بيفضحك|الفضيحه)")
_FLAG_DEADLINE = re.compile(r"(اخر فرصه|خلال ساعه|خلال ساعات|اليوم|امهال|مستعجل)")
_FLAG_VIOLENCE = re.compile(r"(اقتل|اكسر|ساضرب|رح تندم|ادمر|تتالم)")


@lru_cache(maxsize=1)
def _rules() -> dict:
    path = DATA_DIR / "redflags.toml"
    with path.open("rb") as f:
        doc = tomllib.load(f)
    compiled: dict[str, dict] = {}
    for key, cfg in doc["categories"].items():
        compiled[key] = {
            "label": cfg["label"],
            "weight": float(cfg["weight"]),
            "patterns": [
                {"re": p["re"], "regex": re.compile(p["re"]), "boost": float(p["boost"])}
                for p in cfg["patterns"]
            ],
        }
    return compiled


def band_for(score: int) -> tuple[str, str]:
    for ar, en, lo, hi in RISK_BANDS:
        if lo <= score <= hi:
            return ar, en
    return RISK_BANDS[0][0], RISK_BANDS[0][1]


def _empty() -> dict:
    band_ar, band_en = band_for(0)
    return {
        "score": 0,
        "band_ar": band_ar,
        "band_en": band_en,
        "early_warning": False,
        "categories": [],
        "flags": [],
        "keywords": [],
    }


def _flags_from(quotes: list[str]) -> list[str]:
    flags: list[str] = []
    joined = " ".join(quotes)
    if _FLAG_MONEY.search(joined):
        flags.append("طلب مالي / تحويل")
    if _FLAG_PUBLISH.search(joined):
        flags.append("تهديد بالنشر")
    if _FLAG_DEADLINE.search(joined):
        flags.append("ضغط زمني / موعد نهائي")
    if _FLAG_VIOLENCE.search(joined):
        flags.append("تهديد بفعل جسدي")
    return flags


def analyze(text: str) -> dict:
    """يحلل المحتوى ويرجع بنية النتائج الكاملة (درجة، نطاق، فئات، اقتباسات، مؤشرات)."""
    rules = _rules()
    norm_sents = nlp.sentences(text)
    raw_sents = nlp.raw_sentences(text)
    if not norm_sents:
        return _empty()

    total = 0.0
    categories = []
    all_quotes: list[str] = []
    for key, cfg in rules.items():
        sub = 0.0
        hits = []
        seen: set[tuple[str, str]] = set()
        for pat in cfg["patterns"]:
            for i, sent in enumerate(norm_sents):
                if not pat["regex"].search(sent):
                    continue
                dedupe_key = (sent, pat["re"])
                if dedupe_key in seen:
                    continue
                seen.add(dedupe_key)
                sub += cfg["weight"] * pat["boost"]
                quote = raw_sents[i] if i < len(raw_sents) else sent
                hits.append({"quote": quote, "pattern": pat["re"], "boost": pat["boost"], "category": key})
        if hits:
            hits = hits[:MAX_QUOTES_PER_CATEGORY]
            total += sub
            all_quotes.extend(h["quote"] for h in hits)
            categories.append(
                {"key": key, "label": cfg["label"], "subscore": round(sub, 1), "hits": hits}
            )

    score = min(100, int(round(total)))
    band_ar, band_en = band_for(score)
    result = {
        "score": score,
        "band_ar": band_ar,
        "band_en": band_en,
        "early_warning": score >= EARLY_WARNING_MIN_SCORE,
        "categories": categories,
        "flags": _flags_from(all_quotes),
        "keywords": nlp.top_keywords(text),
    }
    log.info("تحليل مكتمل score=%d band=%s categories=%d", score, band_en, len(categories))
    return result