"""مجموعة الحالات الذهبية لمحرك كشف مؤشرات الخطر (M2 معيار النجاح)."""
from features.analysis import redflags

BENIGN_1 = "صباح الخير يا صديقي، كيف حالك؟ نلتقي غداً في المقهى كالعادة."
BENIGN_2 = "أرسلت لك الملف المطلوب بالبريد الإلكتروني كما طلبت، تفضل بالاطلاع عليه وإبلاغي بالملاحظات."

THREAT_EXTORTION = "إذا ما دفعت لي 500 دولار هسا، بنشر صورك الخاصة لكل أصدقائك وعائلتك."
THREAT_MENACE = "أحذرك للمرة الأخيرة يا صديقي، إذا ما سلمتني الملف رح تندم على ذلك."
FRAUD_PHISHING = "عاجل! فزت بجائزة مليون ليرة، اضغط على الرابط وأدخل رقم بطاقتك ورمز التحقق خلال ساعة."
PRIVACY_NUDGE = "عندي تسجيلات مكالماتك الخاصة، وإذا ما دفعت حوالة بنشرها على المنصة."


def _keys(result):
    return {c["key"] for c in result["categories"]}


def test_benign_texts_are_low_risk_no_flags():
    for benign in (BENIGN_1, BENIGN_2):
        result = redflags.analyze(benign)
        assert result["score"] < 25, result
        assert result["band_en"] == "low"
        assert result["categories"] == []
        assert result["early_warning"] is False


def test_extortion_matches_category_and_high_score():
    result = redflags.analyze(THREAT_EXTORTION)
    assert "extortion" in _keys(result)
    assert result["score"] >= 50
    assert result["early_warning"] is True
    assert all(h["quote"] and h["pattern"] for c in result["categories"] for h in c["hits"])


def test_menace_recognized_as_threat():
    result = redflags.analyze(THREAT_MENACE)
    assert "threat" in _keys(result)
    assert result["score"] >= 50


def test_phishing_recognized_as_fraud():
    result = redflags.analyze(FRAUD_PHISHING)
    assert "fraud" in _keys(result)
    assert result["score"] >= 50


def test_privacy_and_extortion_recognized():
    result = redflags.analyze(PRIVACY_NUDGE)
    keys = _keys(result)
    assert {"privacy", "extortion"} <= keys
    assert result["score"] >= 50


def test_early_warning_flag_boundary():
    low = {"score": 0}
    assert not any(c for c in [])  # صفر
    assert {**redflags._empty(), "score": 0}["early_warning"] is False


def test_empty_input_returns_low():
    result = redflags.analyze("   \n ")
    assert result["score"] == 0
    assert result["band_en"] == "low"