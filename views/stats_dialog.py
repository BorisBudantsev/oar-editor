# views/stats_dialog.py

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
    QWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QPushButton, QLabel, QScrollArea
)
from PyQt5.QtCore import Qt

from utils.constants import CATEGORY_PERMANENT
from controllers import export_controller


class StatsDialog(QDialog):
    """Диалог анализа загруженности — три вкладки + кнопки экспорта."""

    def __init__(self, model, report, scale=8, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Анализ загруженности")
        self.resize(1000, 720)

        self.model = model
        self.report = report
        self.scale = scale

        layout = QVBoxLayout(self)

        tabs = QTabWidget()
        tabs.addTab(self._make_employees_tab(report["employees"]),
                    "По сотрудникам")
        tabs.addTab(self._make_workplaces_tab(report["workplaces"]),
                    "По рабочим местам")
        tabs.addTab(self._make_totals_tab(report["totals"]),
                    "Общий итог")
        layout.addWidget(tabs)

        # --- Кнопки ---
        btn_row = QHBoxLayout()

        btn_html = QPushButton("Экспорт HTML")
        btn_html.clicked.connect(self._export_html)
        btn_row.addWidget(btn_html)

        btn_excel = QPushButton("Экспорт Excel")
        btn_excel.clicked.connect(self._export_excel)
        btn_row.addWidget(btn_excel)

        btn_word = QPushButton("Экспорт Word")
        btn_word.clicked.connect(self._export_word)
        btn_row.addWidget(btn_word)

        btn_pdf = QPushButton("Экспорт PDF")
        btn_pdf.clicked.connect(self._export_pdf)
        btn_row.addWidget(btn_pdf)

        btn_row.addStretch()

        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)

        layout.addLayout(btn_row)

    # ------------------------------------------------------------------
    # Экспорт
    # ------------------------------------------------------------------
    def _export_html(self):
        export_controller.export_stats_html(self, self.model, self.report, self.scale)

    def _export_excel(self):
        export_controller.export_stats_excel(self, self.model, self.report, self.scale)

    def _export_word(self):
        export_controller.export_stats_word(self, self.model, self.report, self.scale)

    def _export_pdf(self):
        export_controller.export_stats_pdf(self, self.model, self.report, self.scale)

    # ------------------------------------------------------------------
    def _make_employees_tab(self, rows):
        w = QWidget()
        layout = QVBoxLayout(w)

        table = QTableWidget()
        table.setColumnCount(9)
        table.setHorizontalHeaderLabels([
            "ФИО", "Категория", "Рабочих", "Выходных",
            "Д", "Энд", "Опер", "О/Э", "Коэф. занятости"
        ])
        table.setRowCount(len(rows))
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.verticalHeader().setVisible(False)

        for i, r in enumerate(rows):
            cat = ("постоянный" if r["category"] == CATEGORY_PERMANENT
                   else "совместитель")
            cells = [
                r["name"], cat, str(r["work"]),
                str(r["vyh"]) if r["vyh"] != "" else "—",
                str(r["d_count"]), str(r["endo"]), str(r["oper"]),
                r["o_e_ratio"], r["busy_ratio"] if r["busy_ratio"] else "—",
            ]
            for j, v in enumerate(cells):
                item = QTableWidgetItem(str(v))
                if j >= 2:
                    item.setTextAlignment(Qt.AlignCenter)
                table.setItem(i, j, item)

        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        for c in range(1, 9):
            header.setSectionResizeMode(c, QHeaderView.ResizeToContents)

        layout.addWidget(table)
        return w

    # ------------------------------------------------------------------
    def _make_workplaces_tab(self, wp):
        w = QWidget()
        outer = QVBoxLayout(w)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        scroll.setWidget(inner)
        inner_layout = QVBoxLayout(inner)

        blocks = [
            ("Эндоскопия (ЭНД1+ЭНД2+ЭНД3)", wp["endo"]),
            ("Операционная (З+Б+Ж+К)", wp["oper"]),
            ("Дежурства (Д)", wp["d"]),
            ("Отношение Опер/Энд", wp["ratio"]),
            ("Коэффициент занятости (совместители)", wp["busy"]),
        ]

        for title, rows in blocks:
            lbl = QLabel(title)
            lbl.setStyleSheet("font-weight: bold; padding-top: 8px;")
            inner_layout.addWidget(lbl)

            table = QTableWidget()
            table.setColumnCount(2)
            table.setHorizontalHeaderLabels(["Сотрудник", "Значение"])
            table.setRowCount(len(rows))
            table.setEditTriggers(QTableWidget.NoEditTriggers)
            table.verticalHeader().setVisible(False)

            for i, (name, val) in enumerate(rows):
                table.setItem(i, 0, QTableWidgetItem(str(name)))
                item_val = QTableWidgetItem(str(val))
                item_val.setTextAlignment(Qt.AlignCenter)
                table.setItem(i, 1, item_val)

            header = table.horizontalHeader()
            header.setSectionResizeMode(0, QHeaderView.Stretch)
            header.setSectionResizeMode(1, QHeaderView.ResizeToContents)

            table.setMinimumHeight(min(40 + 24 * len(rows), 300))
            inner_layout.addWidget(table)

        inner_layout.addStretch()
        outer.addWidget(scroll)
        return w

    # ------------------------------------------------------------------
    def _make_totals_tab(self, totals):
        w = QWidget()
        layout = QVBoxLayout(w)

        text = (
            f"Всего смен ЭНД1+ЭНД2+ЭНД3: {totals['endo']}\n\n"
            f"Всего смен З+Б+Ж+К: {totals['oper']}\n\n"
            f"Всего смен Ж: {totals['zh']}"
        )
        lbl = QLabel(text)
        lbl.setStyleSheet("font-size: 14pt; padding: 20px; line-height: 1.6;")
        layout.addWidget(lbl)
        layout.addStretch()
        return w