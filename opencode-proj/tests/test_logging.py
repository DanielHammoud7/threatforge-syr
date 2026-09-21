import logging
import time

import pytest

from config import LOGS_DIR
from core.logging import get_logger, setup_logging


def test_logging_is_async_queue_based():
    root = setup_logging(logging.INFO)
    handler_types = [type(h).__name__ for h in root.handlers]
    assert "QueueHandler" in handler_types, handler_types
    assert getattr(root, "_tf_listener", None) is not None


def test_log_written_to_rotating_file(tmp_path):
    setup_logging(logging.DEBUG)
    log = get_logger("tests.logging")
    marker = f"marker-{time.time_ns()}"
    log.info(marker)
    time.sleep(0.15)  # إتاحة الخيط اللاحظر للكتابة
    content = (LOGS_DIR / "app.log").read_text(encoding="utf-8")
    assert marker in content
    assert "INFO" in content