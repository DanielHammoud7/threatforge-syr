"""طبقة الواجهة المشتركة (UI) — CSS مخصص + شارة نطاق الخطر.

تُركّز كل التنسيقات البصرية لـ Streamlit هنا (بلا أي منطق خلفي) لتشاركها app.py
دون تكرار (Protocol 2 — DRY في PROJECT_MAP.md). لا تُستدعى أي من ميزات التحليل.

لوحة الألوان تعتمد على متغيرات سمة Streamlit الأساسية (--text-color، --background-color،
--secondary-background-color، --primary-color) التي تتبدل تلقائياً بين الوضعين Light/Dark،
فتضمن تبايناً عالياً ومقروءية كاملة في الحالتين دون ترميز ألوان ثابتة للنصوص.
"""
from __future__ import annotations

import streamlit as st

# ألوان نطاقات الخطر (عرض بصري فقط — لا تدخل في تقدير التحليل).
# درجات 700 من Slate/Green/Amber/Orange/Red: نسبة تباين أبيض ≥ 4:1 (AA) للنص العريض.
BAND_HEX = {
    "low": "#15803d",       # green-700  — تباين أبيض ≈ 4.7:1
    "medium": "#a16207",    # yellow-700 — تباين أبيض ≈ 4.4:1
    "high": "#c2410c",      # orange-700 — تباين أبيض ≈ 4.2:1
    "critical": "#b91c1c",  # red-700    — تباين أبيض ≈ 5.9:1
}

CUSTOM_CSS = """
<style>
:root {
  /* توكينز أساسية مأخوذة من سمة Streamlit الفعلية (تتبع Light/Dark تلقائياً) */
  --tf-ink: var(--text-color);                       /* النص الأساسي بعكس الخلفية تماماً */
  --tf-soft: var(--secondary-background-color);      /* خلفية البطاقات (فاتح/داكن تلقائياً) */
  --tf-muted: color-mix(in srgb, var(--text-color) 68%, transparent);
  --tf-line: color-mix(in srgb, var(--text-color) 16%, transparent);
  /* Dark Navy في الوضع الفاتح، وأزرق فاتح في الوضع الداكن */
  --tf-brand: #0d2f52;
}

@media (prefers-color-scheme: dark) {
  :root {
    --tf-brand: #a8c7fa;
  }
}

.stApp {
  font-family: "Segoe UI", "Noto Naskh Arabic", Tahoma, sans-serif;
  color: var(--tf-ink);
}

.block-container {
  padding-top: 2.4rem;
  padding-bottom: 3.2rem;
  max-width: 920px;
  margin-inline: auto;
}

/* ── الترويسة (نص بعكس الخلفية + شريط تمييز) ── */
[data-testid="stHeading"] h1 {
  color: var(--tf-ink);
  font-size: 2rem;
  font-weight: 800;
  letter-spacing: -0.4px;
}
[data-testid="stHeading"] h1::after {
  content: "";
  display: block;
  width: 54px;
  height: 4px;
  border-radius: 2px;
  background: var(--tf-brand);
  margin-top: 8px;
}

/* ── عناوين الأقسام (نص عالي التباين + شريط تمييز) ── */
h2, h3 {
  color: var(--tf-ink);
  font-weight: 800;
  margin-top: 1.4rem;
  letter-spacing: -0.2px;
}
h2::after, h3::after {
  content: "";
  display: block;
  width: 42px;
  height: 3px;
  border-radius: 2px;
  background: var(--tf-brand);
  margin-top: 6px;
}

/* ── بطاقة المقدمة ── */
.tf-intro {
  background: var(--tf-soft);
  border: 1px solid var(--tf-line);
  border-radius: 14px;
  padding: 13px 18px;
  color: var(--tf-ink);
  font-size: 0.95rem;
  line-height: 1.7;
  margin: 6px 0 16px;
}

/* ── شارة نطاق الخطر (S3): أبيض صريح على درجات 700 + إطار تمييزي ── */
.tf-risk {
  display: inline-block;
  border-radius: 999px;
  padding: 6px 16px;
  color: #ffffff;
  font-weight: 700;
  font-size: 0.88rem;
  box-shadow: 0 1px 3px rgba(16, 24, 40, 0.18),
              inset 0 0 0 1px rgba(255, 255, 255, 0.20);
  margin: 2px 0 12px;
}

/* ── بطاقات المؤشرات (خلفية سمة تلقائية + نص عكسي كامل) ── */
[data-testid="stMetric"] {
  background: var(--tf-soft);
  border: 1px solid var(--tf-line);
  border-radius: 14px;
  padding: 12px 14px;
  box-shadow: 0 1px 2px rgba(16, 24, 40, 0.05);
}
[data-testid="stMetric"] label {
  color: var(--tf-muted);
  font-size: 0.84rem;
  font-weight: 700;
}
[data-testid="stMetricValue"] {
  font-size: 1.5rem;
  font-weight: 800;
  color: var(--tf-ink);
}

/* ── شريط التقدم ── */
[data-testid="stProgress"] [role="progressbar"] {
  border-radius: 8px;
  background: linear-gradient(90deg, var(--tf-brand), #2563eb);
}

/* ── التنبيهات (حدود ملونة واضحة عن الخلفية) ── */
[data-testid="stAlert"] {
  border-radius: 12px;
  border-inline-start: 4px solid currentColor;
}

/* ── الحقول والأزرار ── */
.stTextArea textarea,
.stTextInput input,
[data-testid="stFileUploaderDropzone"] {
  border-radius: 10px;
  border-color: var(--tf-line);
}
.stTextArea textarea:focus,
.stTextInput input:focus {
  border-color: var(--tf-brand);
  box-shadow: 0 0 0 2px rgba(13, 47, 82, 0.12);
}
.stButton button,
[data-testid="stFormSubmitButton"] button,
.stDownloadButton button {
  border-radius: 10px;
  font-weight: 600;
  transition: transform 0.12s ease, box-shadow 0.12s ease;
}
.stButton button:hover,
[data-testid="stFormSubmitButton"] button:hover {
  box-shadow: 0 3px 8px rgba(16, 24, 40, 0.18);
  transform: translateY(-1px);
}

/* ── أكورديون الفئات ── */
[data-testid="stExpander"] {
  border: 1px solid var(--tf-line);
  border-radius: 12px;
  background: var(--tf-soft);
  margin-bottom: 6px;
}

/* ── التفريغ النصي القانوني (S4) ── */
[data-testid="stMarkdown"] p {
  line-height: 1.85;
}
</style>
"""


def inject_css() -> None:
    """يحقن ورقة الأنماط المخصصة في الواجهة."""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def risk_badge(band_ar: str, band_en: str) -> str:
    """شارة نطاق الخطر (HTML) تُعرض فوق مؤشرات S3 بلون النطاق عالي التباين."""
    color = BAND_HEX.get(band_en.lower(), "#475569")
    return (
        f'<span class="tf-risk" style="background-color:{color};">'
        f"{band_ar} ({band_en})</span>"
    )