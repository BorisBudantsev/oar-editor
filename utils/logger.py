# utils/logger.py

"""Настройка логирования приложения.

Логи пишутся:
  - в собранном .exe: %APPDATA%\\OAR_Doctors\\logs\\app.log
                       %APPDATA%\\OAR_Nurses\\logs\\app.log
  - из исходников:    <проект>/data/logs/app.log

Ротация: до 1 МБ на файл, до 5 архивных копий (app.log.1, app.log.2, ...).

Настраивается один раз при старте (см. main.py). Модули используют
logging.getLogger(__name__).

Важно: в логи НЕ попадают содержимое ячеек, ФИО сотрудников,
примечания и другие персональные данные. Логируем только пути,
форматы, размеры, коды ошибок.
"""

import logging
import logging.handlers
import os
import sys

from app_config import get


LOG_FILE_NAME = "app.log"
LOG_DIR_NAME = "logs"
MAX_BYTES = 1 * 1024 * 1024   # 1 МБ
BACKUP_COUNT = 5
LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_configured = False


def get_log_dir():
    """Путь к папке с логами (без создания)."""
    if getattr(sys, "frozen", False):
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        return os.path.join(base, get("data_folder"), LOG_DIR_NAME)
    # Из исходников — рядом с папкой data/
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(project_root, "data", LOG_DIR_NAME)


def get_log_path():
    """Полный путь к файлу лога."""
    return os.path.join(get_log_dir(), LOG_FILE_NAME)


def setup_logging(level=logging.INFO, log_dir=None, force=False):
    """Настраивает корневой logger. Идемпотентно.

    log_dir — необязательный путь (для тестов).
    force   — переопределить существующую настройку (для тестов).

    При ошибке создания папки/файла печатает в stderr и переходит на
    вывод в stderr — приложение не должно падать из-за логирования.
    """
    global _configured
    if _configured and not force:
        return

    root = logging.getLogger()
    root.setLevel(level)

    # Снимаем возможные дефолтные handlers
    for h in list(root.handlers):
        root.removeHandler(h)

    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    try:
        target_dir = log_dir if log_dir is not None else get_log_dir()
        os.makedirs(target_dir, exist_ok=True)
        log_path = os.path.join(target_dir, LOG_FILE_NAME)

        handler = logging.handlers.RotatingFileHandler(
            log_path,
            maxBytes=MAX_BYTES,
            backupCount=BACKUP_COUNT,
            encoding="utf-8",
        )
        handler.setFormatter(formatter)
        root.addHandler(handler)
    except Exception as e:
        print(f"[logger] Не удалось настроить файловый лог: {e}",
              file=sys.stderr)
        stderr_handler = logging.StreamHandler(sys.stderr)
        stderr_handler.setFormatter(formatter)
        root.addHandler(stderr_handler)

    _configured = True


def install_excepthook():
    """Логирует необработанные исключения и вызывает стандартный hook.

    В .exe с console=False стандартный traceback уходит в никуда, поэтому
    дополнительно пишем его в лог через logging.critical.
    """
    original = sys.excepthook

    def _hook(exc_type, exc_value, exc_tb):
        logging.getLogger("unhandled").critical(
            "Необработанное исключение",
            exc_info=(exc_type, exc_value, exc_tb),
        )
        original(exc_type, exc_value, exc_tb)

    sys.excepthook = _hook