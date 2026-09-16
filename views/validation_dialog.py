# views/validation_dialog.py

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton
)
from PyQt5.QtCore import Qt


class ValidationDialog(QDialog):
    """Диалог с результатами проверки графика."""

    def __init__(self, errors, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Результат проверки")
        self.resize(760, 520)

        layout = QVBoxLayout(self)

        if not errors:
            msg = QLabel("Ошибок не обнаружено.")
            msg.setStyleSheet("font-size: 12pt; padding: 20px;")
            layout.addWidget(msg)
        else:
            days_with_errors = len(set(e["day"] for e in errors))
            header = QLabel(
                f"Найдено ошибок: {len(errors)}. "
                f"Проблемных дней: {days_with_errors}."
            )
            header.setStyleSheet("font-weight: bold; padding: 4px;")
            layout.addWidget(header)

            table = QTableWidget()
            table.setColumnCount(3)
            table.setHorizontalHeaderLabels(["День", "Правило", "Описание"])
            table.setRowCount(len(errors))
            table.setEditTriggers(QTableWidget.NoEditTriggers)
            table.verticalHeader().setVisible(False)

            for i, err in enumerate(errors):
                item_day = QTableWidgetItem(str(err["day"]))
                item_day.setTextAlignment(Qt.AlignCenter)
                item_rule = QTableWidgetItem(err["rule"])
                item_msg = QTableWidgetItem(err["message"])

                table.setItem(i, 0, item_day)
                table.setItem(i, 1, item_rule)
                table.setItem(i, 2, item_msg)

            header_view = table.horizontalHeader()
            header_view.setSectionResizeMode(0, QHeaderView.ResizeToContents)
            header_view.setSectionResizeMode(1, QHeaderView.ResizeToContents)
            header_view.setSectionResizeMode(2, QHeaderView.Stretch)

            layout.addWidget(table)

        # Кнопка закрытия
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)