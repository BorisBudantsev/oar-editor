# utils/resources.py

"""Доступ к ресурсам проекта (иконки и т.п.).

Работает одинаково и при запуске из исходников, и из собранного `.exe`
(PyInstaller распаковывает ресурсы во временную папку `sys._MEIPASS`).
"""

import os
import sys


def resource_path(relative_path):
    """Возвращает абсолютный путь к ресурсу.

    ``relative_path`` задаётся от корня проекта, например
    ``assets/icons/save.svg``.

    - из `.exe` — путь внутри распакованной временной папки ``_MEIPASS``;
    - из исходников — от корня проекта (на два уровня выше этого файла),
      а не от текущего каталога, из которого запущен интерпретатор.
    """
    if hasattr(sys, "_MEIPASS"):
        base_dir = sys._MEIPASS
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, relative_path)
