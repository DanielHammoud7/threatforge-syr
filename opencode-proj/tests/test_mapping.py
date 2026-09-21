from features.analysis import redflags
from features.legal import mapping
from tests.test_redflags import THREAT_EXTORTION, BENIGN_1


def test_legal_qualification_maps_extortion_to_article_20():
    result = mapping.legal_qualification(redflags.analyze(THREAT_EXTORTION))
    assert "المادة 20" in result["refs"]
    assert "الابتزاز والتهديد الإلكتروني" in result["labels"]
    assert result["narrative"]
    assert "قانون الجريمة المعلوماتية رقم 20 لعام 2022" in result["law"]


def test_legal_qualification_clean_benign_has_no_refs():
    result = mapping.legal_qualification(redflags.analyze(BENIGN_1))
    assert result["refs"] == []
    assert result["labels"] == []
    assert "لم تظهر" in result["narrative"]


def test_legal_mapping_file_is_valid_and_keyed():
    _, offenses = mapping._offenses()
    assert set(offenses) >= {"extortion", "fraud", "privacy"}
    for key, off in offenses.items():
        assert off["label"] and off["articles"] and off["template"]