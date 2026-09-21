from features.analysis import nlp


def test_normalize_maps_hamza_and_ta_marbuta():
    assert nlp.normalize("أحمر إشارة ة آية") == "احمر اشاره ه ايه"
    assert nlp.normalize("مُتَعَلِّم") == "متعلم"


def test_normalize_strips_tatweel_and_bidi_marks():
    assert nlp.normalize("كلمة\u0640\u0640 ط\u200fويل") == "كلمه طويل"


def test_sentences_split_on_arabic_punct_keeping_marks():
    text = "مرحبا! كيف حالك؟ سأنشرها."
    sents = nlp.sentences(text)
    assert len(sents) == 3
    assert sents[0] == "مرحبا!"


def test_raw_sentences_preserve_original_glyphs():
    text = "أهلاً بك! كيف حالك؟"
    raw = nlp.raw_sentences(text)
    assert raw[0] == "أهلاً بك!"
    assert "أ" in raw[0]  # غير مطبّع


def test_tokenize_removes_arabic_stopwords():
    tokens = nlp.tokenize("من في على البيانات السرية تحميل")
    assert "من" not in tokens
    assert "في" not in tokens
    assert "البيانات" in tokens


def test_top_keywords_ranks_by_frequency():
    kws = nlp.top_keywords("دفع دفع دفع صور صور مبلغ", limit=3)
    assert kws[0] == "دفع"
    assert "صور" in kws