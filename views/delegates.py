# views/delegates.py

from PyQt5.QtWidgets import QStyledItemDelegate, QComboBox
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QPen
from utils.constants import (
    CODES_PERMANENT, SPECIAL_VALUES, WORKPLACE_CODES,
    CATEGORY_PERMANENT, CATEGORY_PARTTIME, CLEAR_LABEL
)


class WideComboBox(QComboBox):
    """QComboBox с попапом, расширяющимся по самой длинной строке."""
    def showPopup(self):
        fm = self.fontMetrics()
        max_w = 0
        for i in range(self.count()):
            w = fm.horizontalAdvance(self.itemText(i))
            if w > max_w:
                max_w = w
        self.view().setMinimumWidth(max(max_w + 40, 80))
        super().showPopup()


class ScheduleDelegate(QStyledItemDelegate):
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller

    # ------------------------------------------------------------------
    # Граница снизу под последним постоянным
    # ------------------------------------------------------------------
    def paint(self, painter, option, index):
        super().paint(painter, option, index)

        if index.row() == self.controller.last_permanent_row:
            painter.save()
            pen = QPen(QColor(60, 60, 60))
            pen.setWidth(3)
            painter.setPen(pen)
            r = option.rect
            painter.drawLine(r.left(), r.bottom() - 1, r.right(), r.bottom() - 1)
            painter.restore()

    # ------------------------------------------------------------------
    # Создание выпадающего списка
    # ------------------------------------------------------------------
    def createEditor(self, parent, option, index):
        col = index.column()
        if col < 2:
            return None

        row_type, data = self.controller.get_row_info(index.row())
        current = index.data(Qt.DisplayRole) or ""

        if row_type == 'employee':
            if data['category'] == CATEGORY_PERMANENT:
                values = list(CODES_PERMANENT) + [CLEAR_LABEL]
            else:  # совместитель
                if current == "":
                    values = ["*", CLEAR_LABEL]
                else:
                    # "*" обязательно в списке, иначе текущее значение не подсветится
                    # и ячейка затрётся при первом же клике вне редактора
                    values = list(WORKPLACE_CODES) + ["*", CLEAR_LABEL]
        elif row_type == 'special':
            values = list(SPECIAL_VALUES) + [CLEAR_LABEL]
        else:
            return None

        combo = WideComboBox(parent)
        combo.addItems(values)

        if current and combo.findText(current) >= 0:
            combo.setCurrentIndex(combo.findText(current))
        else:
            i = combo.findText(CLEAR_LABEL)
            if i >= 0:
                combo.setCurrentIndex(i)

        return combo

    # ------------------------------------------------------------------
    def setEditorData(self, editor, index):
        value = index.data(Qt.DisplayRole) or ""
        if value:
            i = editor.findText(value)
            if i >= 0:
                editor.setCurrentIndex(i)

    # ------------------------------------------------------------------
    def setModelData(self, editor, model, index):
        value = editor.currentText()
        row_type, data = self.controller.get_row_info(index.row())
        current = index.data(Qt.DisplayRole) or ""

        if row_type == 'employee':
            emp = data
            if emp['category'] == CATEGORY_PARTTIME:
                if value == CLEAR_LABEL:
                    if current in WORKPLACE_CODES:
                        value = "*"
                    else:
                        value = ""
            else:  # постоянный
                if value == CLEAR_LABEL:
                    value = ""

        elif row_type == 'special':
            if value == CLEAR_LABEL:
                value = ""

        else:
            return

        model.setData(index, value, Qt.EditRole)