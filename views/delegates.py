# views/delegates.py

from PyQt5.QtWidgets import QStyledItemDelegate, QComboBox, QLineEdit
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QPen
from utils.constants import CLEAR_LABEL
from utils.rules import (
    allowed_values,
    allowed_special_values,
    normalize_on_clear,
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

        if row_type == 'notes':
            editor = QLineEdit(parent)
            editor.setMaxLength(10)
            return editor

        if row_type == 'employee':
            values = list(allowed_values(data, current))
        elif row_type == 'special':
            values = list(allowed_special_values(data))
        else:
            return None

        # UI-метка «очистить» добавляется последней
        values.append(CLEAR_LABEL)

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

        if isinstance(editor, QLineEdit):
            editor.setText(value)
            return

        if value:
            i = editor.findText(value)
            if i >= 0:
                editor.setCurrentIndex(i)

    # ------------------------------------------------------------------
    def setModelData(self, editor, model, index):
        row_type, data = self.controller.get_row_info(index.row())

        if row_type == 'notes':
            value = editor.text()[:10]
            model.setData(index, value, Qt.EditRole)
            return

        value = editor.currentText()
        current = index.data(Qt.DisplayRole) or ""

        if row_type == 'employee':
            if value == CLEAR_LABEL:
                value = normalize_on_clear(data, current)
        elif row_type == 'special':
            if value == CLEAR_LABEL:
                value = ""
        else:
            return

        model.setData(index, value, Qt.EditRole)