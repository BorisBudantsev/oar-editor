# main.py

import sys
import os
import logging

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon

from app_config import get, ROLE
from utils.constants import APP_VERSION
from utils.logger import setup_logging, install_excepthook, get_log_path
from views.main_window import MainWindow


def resource_path(relative_path):
    """Возвращает путь к ресурсу с учётом работы из .exe."""
    if hasattr(sys, "_MEIPASS"):
        # PyInstaller распаковывает ресурсы во временную папку
        return os.path.join(sys._MEIPASS, relative_path)
    # Из исходников — путь относительно самого файла main.py,
    # а не текущего каталога, из которого запущен интерпретатор
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)


if __name__ == "__main__":
    # 1. Логирование — как можно раньше
    setup_logging()
    install_excepthook()

    logger = logging.getLogger(__name__)
    logger.info(
        "Старт приложения: версия=%s, роль=%s, лог=%s",
        APP_VERSION, ROLE, get_log_path(),
    )

    app = QApplication(sys.argv)
    app.setApplicationName(get("app_title"))

    icon_path = resource_path(get("icon"))
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())