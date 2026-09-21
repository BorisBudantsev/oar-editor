# main.py

import sys
import os
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
from views.main_window import MainWindow
from app_config import get


def resource_path(relative_path):
    """Возвращает путь к ресурсу с учётом работы из .exe."""
    if hasattr(sys, "_MEIPASS"):
        # PyInstaller распаковывает ресурсы во временную папку
        return os.path.join(sys._MEIPASS, relative_path)
    # Из исходников — путь относительно самого файла main.py,
    # а не текущего каталога, из которого запущен интерпретатор
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName(get("app_title"))

    icon_path = resource_path(get("icon"))
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())