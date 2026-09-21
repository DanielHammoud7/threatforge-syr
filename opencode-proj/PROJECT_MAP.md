# PROJECT_MAP.md — ThreatForge SYR (دليل الذاكرة الخارجية)

> الحالة: **COMPLETED — v1.0.0 (مرحلة البناء محققة ومتحقق منها)** | آخر تحديث: 2026-09-21 | نقطة مرجعية: Python 3.13.0 (Win)
> الاسم الرمزي: منصة ويب ذكية لكشف التهديدات الرقمية وتوثيق الأدلة الجنائية وفق القانون السوري
> **دليل التحقق:** `40/40` اختبار ناجح (`tests/`) — يشمل اختبار E2E حقيقي: صورة عربية → OCR → تحليل → PDF → تشفير → تحقق.

---

## [TECH_STACK] — إصدارات مثبتة من المستودعات الرسمية (تم التثبيت والتحقق 2026-09-21)

| النطاق | الحزمة | الإصدار المقفول | ملاحظات الموثوقية |
|---|---|---|---|
| واجهة الويب | **streamlit** | `1.64.0` | قرار Q1 — لا Flask (لا Feature Creep) |
| OCR | **pytesseract** | `0.3.13` | غلاف لثنائي خارجي Tesseract (اكتشاف تلقائي للمسارات) |
| معالجة صور | **opencv-python** | `5.0.0.93` | مرحلة ما قبل المعالجة (greyscale/upscale/blur/threshold) — API 5.x مُتحقق |
| NLP | **nltk** | `3.10.3` | `RegexpTokenizer` فقط — **بلا تحميل corpora** (قرار إغلاق P-02) |
| توليد PDF | **reportlab** | `5.0.1` | قالب جنائي بمحتوى عربي RTL (خط معد Arial/DejaVu) |
| تشفير/تجزئة | **cryptography** | `50.0.1` | AES-256-GCM + PBKDF2-HMAC-SHA256 (600k)؛ SHA-256 من `hashlib` (stdlib) |
| عرض عربي | **python-bidi** | `0.6.11` | `get_display` لعرض/رسم النصوص العربية صحيح الاتجاه |
| تشكيل عربي | **arabic-reshaper** | `3.0.1` | تشكيل الحروف في PDF (reportlab) واختبارات OCR |
| اختبارات | **pytest** | `9.1.1` | + `streamlit.testing.v1.AppTest` لتشغيل الواجهة كاملة S0→S7 |

**تبعيات خارجية (ليست pip):**
- ثنائي **Tesseract 5.4.0.20240606** (بناء UB-Mannheim) — **موجود/مكتشف** على هذا النظام في `C:\Program Files\Tesseract-OCR\` (يُكتشف تلقائياً عبر `_probe_tesseract` دون الحاجة إلى PATH).
- حزمتا اللغة **`ara` + `eng`** ← **مضمّنتان في المشروع**: `data/tessdata/` (المصدر: `tessdata_fast` عبر jsDelivr)؛ `TESSDATA_PREFIX` يُضبط برمجياً عند أول تشغيل → إعداد **محمول** لا يحتاج تثبيت نظام.
- بيانات NLTK: **غير مطلوبة إطلاقاً** — قائمة stopwords عربية مضمّنة في `data/arabic_stopwords.txt`.

**قرارات تكوين:**
- ملفات الإعداد بصيغة **TOML** (تُقرأ عبر `tomllib` من المكتبة القياسية — صفر تبعيات): `data/redflags.toml` + `data/legal_mapping.toml`.
- حظر صريح: أي ترقية إصدار تمر عبر مراجعة هذا الجدول أولاً.

---

## [SYSTEM_FLOW] — رحلة المستخدم كآلة حالات قابلة للتحقق (GUI)

```
          ┌────────┐     ┌────────┐     ┌───────────┐
 INPUT ──►│ S0     │────►│ S1 OCR │────►│ S2 NLP    │
 نص/صورة │ INGEST │     │ ara+eng│     │ NORMALIZE │
          └────────┘     └────────┘     └───────────┘
                                             │
          ┌───────────┐     ┌────────┐      ▼
          │ S5 REPORT │◄────│ S4 MAP │◄──── S3 ANALYZE
          │ PDF+UTC   │     │ القانون │     │ قواعد موزونة
          └─────┬─────┘     └────────┘     └─► Early Warning
                ▼
          ┌───────────┐     ┌──────────────┐
          │ S6 ENCRYPT│────►│ S7 RESPONSE  │
          │ AES+GCM   │     │ إرشاد+API stub│
          └───────────┘     └──────────────┘
```

**أهداف قابلة للتحقق لكل حالة (شرط الخروج Exit Condition) — كلها محققة في `tests/`:**
- **S0 INGEST**: استلام نص ملصوق أو صورة (PNG/JPG) ← خروج: `content != ""` وإلا رسالة خطأ إجرائية. ✓ (test_app)
- **S1 OCR**: معالجة OpenCV → pytesseract `-l ara+eng` ← خروج: نص مستخرج غير فارغ وإلا إنذار "صورة غير مقروءة". ✓ (test_ocr + test_e2e_ocr_report)
- **S2 NORMALIZE**: تطبيع (تشكيل/ألف/تاء مربوطة) + tokenize + إزالة stopwords ← خروج: `tokens > 0`. ✓ (test_nlp)
- **S3 ANALYZE**: محرك قواعد موزون → درجات فئات + درجة خطر 0–100 + نطاق (low/medium/high/critical) + قائمة أدلة (نمط+اقتباس) ← خروج: بنية JSON كاملة. ✓ (test_redflags)
- **S4 MAP**: فئة → مادة من المرسوم 20/2022 مع صياغة استرشادية ← خروج: `legal_refs` غير فارغ. ✓ (test_mapping)
- **S5 REPORT**: PDF يضم النص الأصلي + النص المستخرج + صورة البيكسل الأصلية + UTC timestamp + القسم القانوني ← خروج: ملف PDF يُفتح ويُتحقق محتواه. ✓ (test_report)
- **S6 ENCRYPT**: SHA-256 للأدلة + AES-256-GCM بمفتاح مشتق PBKDF2 من عبارة سرية + sidecar JSON ← خروج: `report.enc` + `manifest.json` صالحان ومقاومان للتلاعب. ✓ (test_encrypt بأكملها: roundtrip، تلاعب-متن، تلاعب-نص-مشفر، تعديل-مانيفست)
- **S7 RESPONSE**: دليل استجابة سريعة + رقم تتبع حتمي ووصلة لبلاغ الجرائم الإلكترونية ← خروج: الواجهة تعرض المسار كاملاً S0→S7 في جلسة واحدة. ✓ (test_app: رحلة E2E كاملة عبر AppTest)

**تنبيه مبكر (Early Warning)** — مرتبط مباشرة بشرط S3: النطاق `critical` يستدعي لافتة تحذير فورية قبل توليد أي تقرير. ✓ مطبق ومعروض في واجهة S3.

---

## [ARCHITECTURE] — تقطيع فعلي (Surgical / Domain-Driven، بلا Micro-files)

```
opencode-proj/
├─ app.py                  # Streamlit: منسّق الحالات S0→S7 (لا منطق تجاري داخله)
├─ config.py               # مصدر الحقيقة: ثوابت، مسارات، خطوط، معاملات KDF/التقدير، STORAGE_DIR
├─ requirements.txt        # مقفول تماماً على جدول [TECH_STACK]
├─ pytest.ini              # إعدادات مسار الاختبارات
├─ core/
│  └─ logging.py           # مخزن تسجيل لامركزي (QueueHandler + QueueListener + RotatingFileHandler)
│                          # + _SafeStreamHandler (آمن لطرفية cp1256 — لا تكسر عند عربي)
├─ features/               # تقسيم بالميزة (نطاق مطلوب فقط)
│  ├─ ingestion/ocr.py     # S0+S1: decode + OpenCV preprocess + pytesseract + _probe_tesseract
│  ├─ analysis/nlp.py      # S2: تطبيع + tokenize (RegexpTokenizer) + stopwords مضمّنة
│  ├─ analysis/redflags.py # S3: محرك قواعد وزني حتمي يحمّل data/redflags.toml
│  ├─ legal/mapping.py     # S4: فئة ← مادة + صياغة قانونية استرشادية (data/legal_mapping.toml)
│  ├─ report/generate.py   # S5: تجميع ReportLab (RTL عبر arabic_reshaper + python-bidi)
│  └─ evidence/encrypt.py  # S6: SHA-256 + AES-256-GCM (AAD) + PBKDF2 + sidecar؛ persist/decrypt/verify
├─ data/
│  ├─ redflags.toml        # الأنماط والأوزان (قابلة للتدقيق والتعديل بدون كود)
│  ├─ legal_mapping.toml   # خريطة الفئات ← مواد المرسوم 20/2022 + قوالب الصياغة
│  ├─ arabic_stopwords.txt # قائمة stopwords عربية (بديل تنزيل NLTK — صفر إنترنت)
│  └─ tessdata/            # ara.traineddata + eng.traineddata (تجهيز محمول، TESSDATA_PREFIX)
├─ storage/                # مخرجات الأدلة (gitignored)
│  └─ evidence/<date>/<case_id>/  # report.pdf (نسخة مساعدة) + report.enc (الحزمة الحجّة) + manifest.json
├─ tests/                  # 8 ملفات اختبار — 40 اختباراً (ذهبية، نتيجة متوقعة مثبتة)
└─ .gitignore              # storage/ ، logs/ ، .venv/ ، __pycache__/
```

**القرارات المغلقة (ADR-lite):**
1. **Streamlit لا Flask** — كبسولة واحدة، حالة مدمجة؛ يخدم غير التقنيين، أقل كود. ✓
2. **محرك قواعد حتمي + NLP لا sklearn** — صفر بيانات تدريب متاحة؛ قابلية تفسير أمام المحكمة؛ ML مستقبلي خلف Feature Flag مؤجل. ✓
3. **Local-first** — المفتاح يُشتق من عبارة سرية عند الطلب، **لا يُخزَّن أبداً**؛ البصمة SHA-256 مستقلة عن المفتاح. ✓
4. **AES-256-GCM مع AAD** يربط النص المشفر بالبصمة والطابع الزمني — أي تعديل بايت واحد = فشل مصادقة + خلل digest. ✓
5. **OCR عربي+إنجليزي** (`ara+eng`) + مسار لصق نص — يطابق السياق السوري وموجز المتطلبات. ✓
6. **إعداد محمول لـ Tesseract** — الثنائي يُكتشف تلقائياً (PATH أو مسارات معروفة) وحزمتا اللغة ضمن `data/tessdata`. ✓

**عقد البيانات (Data Contracts):**
- `redflags.toml` ← `categories[].patterns[] {re, boost}` + `categories[].weight`؛ تحليل على سطور جملية. ✓
- ناتج التحليل JSON: `{score, band_ar, band_en, early_warning, categories[], hits[]:{pattern_id, quote, weight}, keywords[]}` ✓
- `manifest.json`: `{case_id, created_utc, sha256_report, sha256_original_image, risk, legal_refs[], kdf, iterations, cipher, salt_b64, nonce_b64, aad_sha256}` ✓

---

## [ORPHANS & PENDING] — رصيد المتابعة (فارغ من النواقص، بند مؤجّلان موثقان)

| المعرّف | البند | الحالة |
|---|---|---|
| P-01 | ثنائي Tesseract + حزمتا `ara`/`eng` | **مكتمل** — الثنائي 5.4.0 موجود ومكتشف تلقائياً (Program Files)؛ الحزمتان مضمّنتان في `data/tessdata` (محمول عبر `TESSDATA_PREFIX`). توثيق لآلات أخرى في README |
| P-02 | تحميل corpora NLTK | **أُغلق بالتصميم** — `RegexpTokenizer` + stopwords عربية مضمّنة (`data/arabic_stopwords.txt`)؛ يعمل دون إنترنت |
| P-03 | تربيط أرقام المواد الفعلي بالمرسوم 20/2022 | **مكتمل بتنفيذ مؤرّخ + إخلاء مسؤولية** — المواد مثبتة في `data/legal_mapping.toml` من مصادر مرجعية (SCM 2022، مكتب غرس 2026): الابتزاز/التهديد → المادة 20؛ الاحتيال → 16 و17؛ الخصوصية → 21 و22. **خارج نطاق التوصيف:** الذم/القدح (تعارض مصادر حول رقم المادة) — لا يُدرج في التقرير. التقرير والواجهة يعرضان "توصيف استرشادي" + إخلاء مسؤولية. المراجعة القانونية الختامية قبل الاستعمال القضائي **مسؤولية المستخدم/المستشار** (خارج قدرة الكود — موثق) |
| P-04 | شهادة الوقت (NTP/TSA) — حالياً UTC من ساعة النظام | **مؤجل موثق** (خارج نطاق MVP المعتمد؛ UTC النطاق الزمني مسجل في الحزمة) |
| P-05 | "الربط البرمجي للجهات" — Stub حتمي فقط (رقم تتبع) | **مؤجل موثق** (واجهة HTTP مستقبلية — خارج النطاق المعتمد) |
| P-06 | توثيق تثبيت Tesseract للمستخدم النهائي | **مكتمل** — `README.md` يحوي متطلبات التشغيل الكاملة + مسارات الاكتشاف التلقائي |
| P-07 | Fixtures الذهبية (محادثات/صور عربية) | **مكتمل** — `tests/test_redflags.py` (6 حالات ذهبية مثبتة درجاتها) + مولّد صور عربية في `test_ocr.py`/`test_e2e_ocr_report.py` |
| P-08 | تكامل OpenCV 5.0 مع pytesseract | **مكتمل ومُتحقق** — سلسلة المعالجة (greyscale/upscale/blur/threshold) تمر عبر اختبار E2E حتى OCR ناجح |

> **لا نواقص معلقة** — كل صف أعلاه في حالة نهائية (مكتمل أو مؤجل موثق ضمن النطاق).

---

## [VERIFICATION LOG] — سجل التحقق (نص Protocol 2)

- `pytest tests/` → **40 passed** (0 فشل) — آخر تشغيل كامل نظيف.
- تغطية S0→S7 عبر `AppTest.from_file(app.py)` (رحلة E2E كاملة في واجهة حقيقية).
- اختبار E2E حقيقي: صورة عربية مُشكّلة → OCR → تحليل (درجة عالية) → PDF → تشفير → `verify_integrity` = صحيح → فك تشفير = مطابق → عبارة خاطئة تُرفض (المصادقة تتصدى).
- اختبار تلاعب الأدلة: تعديل `report.enc` بايت واحد → رفض مصادقة؛ تعديل `report.pdf` → digest معنّف؛ تعديل `manifest.json` → فشل AAD.

---

## تقييم الأمان (ملاحظات العمارة)
- **حدود التشفير**: محلي أولاً؛ التقرير يُفك تشفيره بعبارة سرية المستخدم فقط — لا سيرفر يملك مفاتيح.
- **معيار الحفظ**: PBKDF2-HMAC-SHA256, 600k تكرار؛ GCM يمنح authenticated = دحض أي ادعاء "فوتوشوب".
- **خصوصية**: لا رفع لأي محتوى خارج الجهاز في Local-first؛ البصمة تحفظ المحتوى كما هو (لا يمكن إثبات تعديل دون تغيير hash).
- **التسجيل الآمن**: منطق التسجيل لا يتضمن نص المحتوى؛ المخرجات في `logs/` (gitignored).