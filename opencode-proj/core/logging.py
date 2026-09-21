"""نظام تسجيل لامركزي (غير حظري) عبر queue.Queue + QueueListener.

- المستويات الأساسية فقط: DEBUG / INFO / WARNING / ERROR.
- كاتب خيط واحد (daemon) يفصل I/O عن المسار الحرج — لا كتلة على التنفيذ الرئيسي.
- لا تبعيات خارجية: stdlib logging.
"""
from __future__ import annotations

import logging
import logging.handlers
import queue
import sys
from pathlib import Path

from config import LOGS_DIR

_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
_DATEFMT = "%Y-%m-%d %H:%M:%S"
_CONFIGURED_FLAG = "_tf_logging_configured"


def _formatter() -> logging.Formatter:
    return logging.Formatter(_FORMAT, _DATEFMT)


class _SafeStreamHandler(logging.StreamHandler):
    """معالج كونسول يتحمّل cp1256/ASCII — يستبدل المحارف غير القابلة للترميز بدل الانهيار."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            stream = self.stream
            enc = getattr(stream, "encoding", None) or "utf-8"
            stream.write(msg.encode(enc, errors="replace").decode(enc, errors="replace") + self.terminator)
            self.flush()
        except Exception:
            self.handleError(record)


def _handlers(console_level: int) -> list[logging.Handler]:
    console = _SafeStreamHandler(sys.stdout)
    console.setLevel(console_level)
    console.setFormatter(_formatter())
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    rotating = logging.handlers.RotatingFileHandler(
        LOGS_DIR / "app.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    rotating.setLevel(logging.DEBUG)
    rotating.setFormatter(_formatter())
    return [console, rotating]


def setup_logging(console_level: int = logging.INFO) -> logging.Logger:
    """تهيئة الجذر مرة واحدة (محروس ضد إعادة التشغيل في جلسات Streamlit)."""
    root = logging.getLogger()
    if getattr(root, _CONFIGURED_FLAG, False):
        return root
    root.setLevel(logging.DEBUG)
    q: queue.Queue[logging.LogRecord] = queue.Queue(-1)
    root.addHandler(logging.handlers.QueueHandler(q))
    listener = logging.handlers.QueueListener(q, *_handlers(console_level))
    listener.start()
    setattr(root, _CONFIGURED_FLAG, True)
    setattr(root, "_tf_listener", listener)
    setattr(root, "_tf_queue", q)
    logging.getLogger(__name__).info("نظام التسجيل اللاحلظي مفعّل (QueueHandler→QueueListener)")
    return root


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)