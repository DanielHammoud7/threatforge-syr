"""ربط النتائج بالتوصيف القانوني — قانون الجريمة المعلوماتية رقم 20 لعام 2022.

الخريطة (فئة ← مواد/عقوبة/سرد) قابلة للتعديل في data/legal_mapping.toml دون كود،
ومرفقة بإخلاء مسؤولية: التوصيف استرشادي ويُتحقق مقابل النص الرسمي قبل التقديم القضائي.
"""
from __future__ import annotations

import logging
import tomllib
from datetime import datetime
from functools import lru_cache

from config import DATA_DIR

log = logging.getLogger(__name__)

OFFENSE_BY_CATEGORY = {
    "extortion": "extortion",
    "threat": "threat",
    "fraud": "fraud",
    "privacy": "privacy",
}


@lru_cache(maxsize=1)
def _offenses() -> tuple[dict, dict]:
    path = DATA_DIR / "legal_mapping.toml"
    with path.open("rb") as f:
        doc = tomllib.load(f)
    return doc["meta"], doc["offenses"]


def legal_qualification(analysis: dict) -> dict:
    """يُرجع التوصيف القانوني للفئات المرصودة (مواد، عقوبات، سرد قانوني، إخلاء مسؤولية)."""
    meta, offenses = _offenses()
    labels: list[str] = []
    refs: list[str] = []
    paragraphs: list[str] = []
    for cat in analysis.get("categories", []):
        offense_key = OFFENSE_BY_CATEGORY.get(cat.get("key"))
        if not offense_key or offense_key not in offenses:
            continue
        off = offenses[offense_key]
        labels.append(off["label"])
        refs.extend(off["articles"])
        paragraphs.append(off["template"])

    narrative = "\n\n".join(paragraphs) if paragraphs else (
        "لم تظهر الوقائع مؤشرات جريمة معلوماتية ضمن أنماط الفحص الحالية — "
        "لا يُقترح أي توصيف قانوني في هذه المرحلة."
    )
    return {
        "law": meta["law_title"],
        "note": meta["law_note"],
        "refs": sorted(set(refs)),
        "labels": labels,
        "narrative": narrative,
        "documented_at": datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z"),
    }