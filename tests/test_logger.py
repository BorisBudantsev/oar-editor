# tests/test_logger.py

import logging
import os
import sys

from utils import logger as log_module


def test_get_log_path_ends_with_app_log():
    path = log_module.get_log_path()
    assert path.endswith(os.path.join("logs", "app.log"))


def test_get_log_dir_contains_logs():
    d = log_module.get_log_dir()
    assert d.endswith("logs")


def test_setup_logging_writes_file(tmp_path):
    """setup_logging() создаёт файл и пишет в него сообщения."""
    root = logging.getLogger()
    saved_handlers = list(root.handlers)
    try:
        for h in list(root.handlers):
            root.removeHandler(h)

        log_module.setup_logging(log_dir=str(tmp_path), force=True)

        test_logger = logging.getLogger("test_logger")
        test_logger.info("hello from test")
        for h in root.handlers:
            h.flush()

        log_file = tmp_path / "app.log"
        assert log_file.exists()
        content = log_file.read_text(encoding="utf-8")
        assert "hello from test" in content
    finally:
        for h in list(root.handlers):
            h.close()
            root.removeHandler(h)
        for h in saved_handlers:
            root.addHandler(h)
        # сбрасываем флаг, чтобы следующие тесты могли настраивать заново
        log_module._configured = False


def test_setup_logging_is_idempotent(tmp_path):
    """Повторный вызов без force не добавляет второй handler."""
    root = logging.getLogger()
    saved_handlers = list(root.handlers)
    try:
        for h in list(root.handlers):
            root.removeHandler(h)

        log_module.setup_logging(log_dir=str(tmp_path), force=True)
        count_after_first = len(root.handlers)

        log_module.setup_logging(log_dir=str(tmp_path))
        count_after_second = len(root.handlers)

        assert count_after_first == count_after_second
    finally:
        for h in list(root.handlers):
            h.close()
            root.removeHandler(h)
        for h in saved_handlers:
            root.addHandler(h)
        log_module._configured = False


def test_install_excepthook_replaces_hook():
    original = sys.excepthook
    try:
        log_module.install_excepthook()
        assert sys.excepthook is not original
    finally:
        sys.excepthook = original