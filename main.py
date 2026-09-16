# main.py

import sys
import os
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
from views.main_window import MainWindow


def resource_path(relative_path):
    """Возвращает путь к ресурсу с учётом работы из .exe."""
    if hasattr(sys, "_MEIPASS"):
        # PyInstaller распаковывает ресурсы во временную папку
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    icon_path = resource_path("assets/app.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())