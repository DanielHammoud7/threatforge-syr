"""طبقة الواجهة المشتركة (UI) — CSS مخصص + شارة نطاق الخطر.

تُركّز كل التنسيقات البصرية لـ Streamlit هنا (بلا أي منطق خلفي) لتشاركها app.py
دون تكرار (Protocol 2 — DRY في PROJECT_MAP.md). لا تُستدعى أي من ميزات التحليل.
"""
from __future__ import annotations

import streamlit as st

# ألوان نطاقات الخطر (عرض بصري فقط — لا تدخل في تقدير التحليل)
BAND_HEX = {
    "low": "#2e7d32",
    "medium": "#b7791f",
    "high": "#d97706",
    "critical": "#b91c1c",
}

CUSTOM_CSS = """
<style>
:root {
  --tf-ink: #23303e;
  --tf-muted: #5d6b7a;
  --tf-line: #e4e9f0;
  --tf-soft: #f6f8fb;
  --tf-brand: #0d2f52;
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

/* ── الترويسة ── */
[data-testid="stHeading"] h1 {
  font-size: 2rem;
  font-weight: 800;
  letter-spacing: -0.4px;
  color: var(--tf-brand);
}

/* ── عناوين الأقسام ── */
h2, h3 {
  color: var(--tf-brand);
  font-weight: 700;
  margin-top: 1.4rem;
}

/* ── بطاقة المقدمة ── */
.tf-intro {
  background: var(--tf-soft);
  border: 1px solid var(--tf-line);
  border-radius: 14px;
  padding: 13px 18px;
  color: var(--tf-muted);
  font-size: 0.95rem;
  line-height: 1.7;
  margin: 6px 0 16px;
}

/* ── شارة نطاق الخطر (S3) ── */
.tf-risk {
  display: inline-block;
  border-radius: 999px;
  padding: 6px 16px;
  color: #ffffff;
  font-weight: 700;
  font-size: 0.88rem;
  box-shadow: 0 1px 3px rgba(16, 24, 40, 0.18);
  margin: 2px 0 12px;
}

/* ── بطاقات المؤشرات ── */
[data-testid="stMetric"] {
  background: #ffffff;
  border: 1px solid var(--tf-line);
  border-radius: 14px;
  padding: 12px 14px;
  box-shadow: 0 1px 2px rgba(16, 24, 40, 0.05);
}
[data-testid="stMetric"] label {
  color: var(--tf-muted);
  font-size: 0.82rem;
  font-weight: 600;
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

/* ── التنبيهات ── */
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
  background: #ffffff;
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
    """شارة نطاق الخطر (HTML) تُعرض فوق مؤشرات S3 بلون النطاق."""
    color = BAND_HEX.get(band_en.lower(), "#64748b")
    return (
        f'<span class="tf-risk" style="background-color:{color};">'
        f"{band_ar} ({band_en})</span>"
    )