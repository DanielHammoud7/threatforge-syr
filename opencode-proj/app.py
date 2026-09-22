"""ThreatForge SYR — واجهة Streamlit (منسّق رحلة المستخدم S0→S7).

التدفق يتبع [SYSTEM_FLOW] في PROJECT_MAP.md: ادخال → OCR → تحليل → توصيف قانوني →
تقرير PDF → تشفير وأدلة → استجابة ورقم تتبع. الحالة بين الجولات عبر session_state.
"""
from __future__ import annotations

import hashlib
import logging

import streamlit as st

from core.logging import setup_logging
from core.ui import inject_css, risk_badge
import config
from config import APP_NAME, APP_TAGLINE, APP_VERSION, MIN_PASSPHRASE_LEN
from features.analysis import redflags
from features.evidence import encrypt
from features.ingestion import ocr
from features.legal import mapping
from features.report import generate

setup_logging()
log = logging.getLogger("app")

st.set_page_config(page_title=f"{APP_NAME} — كشف وتوثيق", page_icon="🛡️", layout="centered")

inject_css()

st.title(APP_NAME)
st.caption(f"{APP_TAGLINE} · الإصدار {APP_VERSION}")

st.markdown(
    '<div class="tf-intro">' +
    "هذه المنصة تحلل المحتوى المشبوه (نص/لقطة شاشة) لكشف مؤشرات الابتزاز والتهديد "
    "والاحتيال وانتهاك الخصوصية، ثم توثّق الأدلة في تقرير PDF مُشفّر وبصمته SHA-256 تثبت عدم التلاعب."
    + "</div>",
    unsafe_allow_html=True,
)

# ───────────────────────── S0: الادخال ─────────────────────────
st.header("1) جمع الأدلة")
with st.form("ingest_form", clear_on_submit=False):
    pasted = st.text_area(
        "الصق المحادثة المشبوهة هنا (اختياري)",
        key="pasted", height=150,
        placeholder="مثال: لقد حصلت على صورك الخاصة، إذا لم تدفع لي 500 دولار سأنشرها لجميع أصدقائك...",
    )
    uploaded = st.file_uploader(
        "أو ارفع لقطة شاشة (PNG/JPG) — يُستخرج نصها تلقائياً عبر OCR",
        type=["png", "jpg", "jpeg"], key="img_upload",
    )
    submitted = st.form_submit_button("تحليل المحتوى", type="primary")

ocr_text = None
raw_image_bytes = None
raw_image_name = None

if submitted:
    if uploaded is not None:
        if not ocr.is_allowed_image(uploaded.name):
            st.error("صيغة الصورة غير مدعومة — استخدم PNG أو JPG.")
            st.stop()
        if uploaded.size > 15 * 1024 * 1024:
            st.error("حجم الصورة يتجاوز 15 ميجابايت.")
            st.stop()
        raw_image_bytes = uploaded.getvalue()
        raw_image_name = uploaded.name
        try:
            ocr_text = ocr.extract_text_from_image(raw_image_bytes)
        except ocr.ImageDecodeError as exc:
            st.error(str(exc))
            st.stop()
        except ocr.OCRUnavailableError as exc:
            st.error(f"{exc}\n\nيمكنك مواصلة استخدام مسار النص الملصوق فقط.")
            st.stop()

    combined = "\n".join(part for part in (pasted.strip(), ocr_text or "") if part)
    if not combined:
        st.warning("أدخل نصاً أو ارفع صورة أولاً.")
        st.stop()

    analysis = redflags.analyze(combined)
    st.session_state["analysis"] = analysis
    st.session_state["full_text"] = combined
    st.session_state["ocr_text"] = ocr_text or ""
    st.session_state["raw_image_bytes"] = raw_image_bytes
    st.session_state["raw_image_name"] = raw_image_name
    st.session_state["last_case_dir"] = None
    log.info("تحليل: score=%d band=%s len=%d", analysis["score"], analysis["band_en"], len(combined))

# ───────────────────────── S3: النتائج المبكرة ─────────────────────────
analysis = st.session_state.get("analysis")
if analysis is not None:
    st.header("2) نتائج التحليل")
    if analysis["early_warning"]:
        st.error(
            f"⚠️ **تنبيه مبكر:** رُصدت مؤشرات خطر حرجة ({analysis['score']}/100). "
            "لا تدفع أي مبلغ ولا تشارك بيانات إضافية؛ وثّق الأدلة الآن وحافظ على النسخ الأصلية."
        )
    col1, col2, col3 = st.columns(3)
    st.markdown(risk_badge(analysis["band_ar"], analysis["band_en"]), unsafe_allow_html=True)
    col1.metric("مؤشر الخطورة", f"{analysis['score']}/100", analysis["band_ar"])
    col2.metric("الفئات المرصودة", len(analysis["categories"]))
    col3.metric("المؤشرات السلوكية", len(analysis["flags"]))
    st.progress(min(1.0, analysis["score"] / 100))
    if analysis.get("keywords"):
        st.caption("كلمات مفتاحية: " + "، ".join(analysis["keywords"]))
    for cat in analysis["categories"]:
        with st.expander(f"{cat['label']} — درجة الفئة {cat['subscore']}"):
            for hit in cat["hits"]:
                st.markdown(f"- «{hit['quote']}»")
                st.caption(f"النمط: `{hit['pattern']}` · الوزن: {hit['boost']}")
    if not analysis["categories"]:
        st.info("لم تُرصد مؤشرات خطر ضمن أنماط الفحص الحالية — لا توجد إشارة صريحة للابتزاز/التهديد.")

    # ───────────────────────── S4: التوصيف القانوني ─────────────────────────
    st.header("3) التوصيف القانوني")
    legal = mapping.legal_qualification(analysis)
    st.markdown(f"**المرجع:** {legal['law']}")
    st.markdown("**المواد ذات الصلة:** " + ("، ".join(legal["refs"]) if legal["refs"] else "—"))
    for para in legal["narrative"].split("\n\n"):
        st.markdown(para)
    st.caption(f"إخلاء مسؤولية: {legal['note']} (أُنتج هذا التوصيف آلياً {legal['documented_at']})")

    # ───────────────────────── S5+S6: التقرير والتشفير ─────────────────────────
    st.header("4) توثيق الأدلة → تقرير PDF مُشفّر")
    st.markdown(
        "اختر **عبارة سرية** (لا تُخزَّن أبداً) تُشتق منها شارة التشفير AES-256-GCM. "
        "التقرير سيُحفظ بنصه وصورته الأصلية وبصمة SHA-256، ومشفّراً لا يُفتح إلا بعبارتك."
    )
    pw1 = st.text_input("العبارة السرية (8 محارف على الأقل)", type="password", key="pw1")
    pw2 = st.text_input("تأكيد العبارة السرية", type="password", key="pw2")

    if st.button("توليد تقرير الأدلة وتشفيره", key="gen_btn", type="primary"):
        errors = []
        if len(pw1) < MIN_PASSPHRASE_LEN:
            errors.append(f"العبارة السرية يجب أن لا تقل عن {MIN_PASSPHRASE_LEN} محارف.")
        if pw1 != pw2:
            errors.append("العبارتان غير متطابقتين.")
        if errors:
            for err in errors:
                st.error(err)
            st.stop()

        case_id = encrypt.new_case_id()
        created_utc = generate.utc_now_iso()
        report_data = generate.ReportData(
            case_id=case_id,
            created_utc=created_utc,
            analysis=analysis,
            legal=legal,
            original_text=st.session_state.get("full_text", ""),
            ocr_text=st.session_state.get("ocr_text", ""),
            image_bytes=st.session_state.get("raw_image_bytes"),
            image_name=st.session_state.get("raw_image_name"),
            sha256_report="",
        )
        pdf_bytes = generate.build_pdf(report_data)
        report_data.sha256_report = encrypt.sha256_bytes(pdf_bytes)

        case_dir = encrypt.persist_case(
            case_id=case_id,
            pdf_bytes=pdf_bytes,
            image_bytes=raw_image_bytes or st.session_state.get("raw_image_bytes"),
            image_name=raw_image_name or st.session_state.get("raw_image_name"),
            analysis=analysis,
            legal=legal,
            passphrase=pw1,
        )
        st.session_state["last_case_dir"] = str(case_dir)
        st.session_state["last_pdf_bytes"] = pdf_bytes
        log.info("حالة مولّدة: %s dir=%s", case_id, case_dir)
        st.success(f"✅ حُفظت حزمة الأدلة في مجلد الحالة `{case_id}`")

    if st.session_state.get("last_case_dir"):
        case_dir = config.STORAGE_DIR / st.session_state["last_case_dir"]
        verify = encrypt.verify_integrity(case_dir)
        st.markdown(f"**رقم الحالة:** {case_dir.name} · **التوقيت (UTC):** {verify['manifest_created_utc']}")

        col_a, col_b = st.columns(2)
        for fname in sorted(p.name for p in case_dir.iterdir()):
            fbytes = (case_dir / fname).read_bytes()
            st.download_button(
                label=f"تنزيل {fname}", data=fbytes, file_name=fname,
                key=f"dl_{case_dir.name}_{fname}", mime="application/octet-stream",
            )
        if verify["all_ok"]:
            st.success("✓ تحقق السلامة: بصمة التقرير والصورة مطابقتان للمانيفست — لا دليل تلاعب.")
        else:
            st.error("✗ انكسرت تطابقات البصمات — الملفات عدّلت أو تلفت!")

        tracking = hashlib.sha256(case_dir.name.encode("utf-8")).hexdigest()[:10].upper()
        st.info(f"🔎 رقم التتبع (واجهة محاكاة API): `TF-{tracking}` — يمثل المرجع لدى فرع مكافحة الجريمة المعلوماتية.")

    # ───────────────────────── S7: الاستجابة ─────────────────────────
    st.header("5) دليل الاستجابة السريعة")
    st.markdown(
        """
        - **لا تدفع** أي مبلغ ولا تستجب لطلبات المبتز — الاستجابة تزيد الطلب.
        - **لا تغضب** من المبتز ولا تحذف المحادثات أو لقطات الشاشة (أدلة).
        - **لا تشارك** بيانات إضافية أو رموز تحقق مع أي جهة غير موثوقة.
        - **وثّق:** احتفظ بالمحادثة الأصلية كاملةً + التوقيت + عناوين الأرقام/الحسابات.
        - **أبلغ:** قدّم شكوى رسمية لدى النيابة العامة المختصة عبر فرع مكافحة الجريمة المعلوماتية
          (إدارة الأمن الجنائي) — هذا التقرير داعم للشكوى، لا بديل عنها.
        - **أمّن:** غيّر كلمات السر للطرف المتضرر وفعّل المصادقة ثنائية الخطوة على حساباته.
        """
    )
    st.caption(
        "واجهة الربط البرمجي مع الجهات (API Simulation) جاهزة كرقم تتبع حتمي في هذا الإصدار؛ "
        "الربط الفعلي مؤجل وفق المشروع."
    )

    if st.button("🧹 إعادة تعيين الجلسة"):
        for k in ("analysis", "full_text", "ocr_text", "raw_image_bytes", "raw_image_name",
                  "last_case_dir", "last_pdf_bytes"):
            st.session_state.pop(k, None)
        st.rerun()