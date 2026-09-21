"""اختبار التدفق الكامل S0→S7 عبر AppTest (رحلة المستخدم قابلة للتحقق)."""
from pathlib import Path

import config
import pytest
from streamlit.testing.v1 import AppTest

from features.evidence import encrypt
from tests.test_redflags import THREAT_EXTORTION

APP_FILE = Path(__file__).resolve().parent.parent / "app.py"


def _analyze_button(at):
    """زر إرسال نموذج الادخال — key مولّد تلقائياً بصيغة FormSubmitter:ingest_form-..."""
    for b in at.button:
        if b.form_id == "ingest_form":
            return b
    raise AssertionError("زر التحليل غير موجود في الشجرة")


@pytest.fixture()
def at(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "STORAGE_DIR", tmp_path)
    tree = AppTest.from_file(str(APP_FILE), default_timeout=60)
    tree.run()
    return tree


def test_initial_page_loads_cleanly(at):
    assert not at.exception
    assert at.title[0].value == "ThreatForge SYR"


def test_paste_analyze_produces_results(at):
    at.text_area(key="pasted").input(THREAT_EXTORTION)
    _analyze_button(at).click()
    at.run()
    assert not at.exception, at.exception
    assert at.session_state["analysis"]["score"] >= 50
    assert any(m.label == "مؤشر الخطورة" for m in at.metric)


def test_generate_encrypted_report_end_to_end(at, tmp_path):
    at.text_area(key="pasted").input(THREAT_EXTORTION)
    _analyze_button(at).click()
    at.run()
    assert not at.exception, at.exception

    at.text_input(key="pw1").input("secret-pass-123")
    at.text_input(key="pw2").input("secret-pass-123")
    at.button(key="gen_btn").click()
    at.run()
    assert not at.exception, at.exception

    case_dir = tmp_path / at.session_state["last_case_dir"]
    assert (case_dir / "report.pdf").exists()
    assert (case_dir / "report.enc").exists()
    assert (case_dir / "manifest.json").exists()
    assert encrypt.verify_integrity(case_dir)["all_ok"] is True
    assert any("رقم التتبع" in i.value for i in at.info)


def test_wrong_passwords_show_error(at):
    at.text_area(key="pasted").input(THREAT_EXTORTION)
    _analyze_button(at).click()
    at.run()
    at.text_input(key="pw1").input("secret-pass-123")
    at.text_input(key="pw2").input("different-pass")
    at.button(key="gen_btn").click()
    at.run()
    assert any("غير متطابقتين" in e.value for e in at.error)