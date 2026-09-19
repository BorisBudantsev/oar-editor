# controllers/project_controller.py

import calendar
from PyQt5.QtWidgets import QTableWidgetItem, QHeaderView
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QBrush, QColor
from utils.constants import CATEGORY_PERMANENT, CATEGORY_PARTTIME, WORKPLACE_CODES


COLOR_WEEKEND = QColor(219, 219, 219)
COLOR_WEEKDAY = QColor(255, 255, 255)
COLOR_ERROR = QColor(255, 180, 180)


class ProjectController:
    def __init__(self, model, table_widget):
        self.model = model
        self.table = table_widget
        self.row_map = []
        self.last_permanent_row = -1
        self.update_table()
        self.on_change_callback = None   # устанавливается из MainWindow

    # ------------------------------------------------------------------
    def update_table(self):
        model = self.model
        days = model.days_in_month()
        employees = model.employees
        special = model.special

        permanent = [e for e in employees if e['category'] == CATEGORY_PERMANENT]
        parttime = [e for e in employees if e['category'] == CATEGORY_PARTTIME]
        ordered = permanent + parttime

        self.row_map = []
        for emp in ordered:
            self.row_map.append(('employee', emp))
        for key in special.keys():
            self.row_map.append(('special', key))

        if permanent and parttime:
            self.last_permanent_row = len(permanent) - 1
        else:
            self.last_permanent_row = -1

        row_count = len(self.row_map)
        col_count = days + 2

        self.table.blockSignals(True)
        self.table.setRowCount(0)
        self.table.setColumnCount(0)
        self.table.setRowCount(row_count)
        self.table.setColumnCount(col_count)

        WEEKDAY_SHORT = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]

        header_labels = ["№", "ФИО"]
        for d in range(1, days + 1):
            wd = calendar.weekday(model.year, model.month + 1, d)
            header_labels.append(f"{d}\n{WEEKDAY_SHORT[wd]}")
        self.table.setHorizontalHeaderLabels(header_labels)

        # Увеличиваем высоту заголовка, чтобы влезли обе строки
        self.table.horizontalHeader().setFixedHeight(42)
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignCenter)

        emp_number = 0
        for row, (row_type, data) in enumerate(self.row_map):

            if row_type == 'employee':
                emp = data
                emp_number += 1

                item_num = QTableWidgetItem(str(emp_number))
                item_num.setTextAlignment(Qt.AlignCenter)
                item_num.setFlags(Qt.ItemIsEnabled)
                self.table.setItem(row, 0, item_num)

                item_name = QTableWidgetItem(emp['name'])
                item_name.setFlags(Qt.ItemIsEnabled)
                self.table.setItem(row, 1, item_name)

                for day_idx, value in enumerate(emp['days']):
                    item = QTableWidgetItem(value)
                    item.setTextAlignment(Qt.AlignCenter)
                    item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsEditable | Qt.ItemIsSelectable)
                    self.table.setItem(row, 2 + day_idx, item)

            elif row_type == 'special':
                key = data

                item_empty = QTableWidgetItem("")
                item_empty.setFlags(Qt.NoItemFlags)
                self.table.setItem(row, 0, item_empty)

                item_label = QTableWidgetItem(key)
                item_label.setTextAlignment(Qt.AlignCenter)
                item_label.setFlags(Qt.ItemIsEnabled)
                f = item_label.font()
                f.setBold(True)
                item_label.setFont(f)
                self.table.setItem(row, 1, item_label)

                for day_idx, value in enumerate(special[key]):
                    item = QTableWidgetItem(value)
                    item.setTextAlignment(Qt.AlignCenter)
                    item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsEditable | Qt.ItemIsSelectable)
                    self.table.setItem(row, 2 + day_idx, item)

                header = self.table.horizontalHeader()
                # Минимальная ширина столбца дня: чтобы «ЭНД1» влезал
                header.setMinimumSectionSize(28)
        
                # Колонка «№» — фиксированная, нельзя тащить мышью
                header.setSectionResizeMode(0, QHeaderView.Fixed)
                # Колонка «ФИО» — можно тянуть мышью
                header.setSectionResizeMode(1, QHeaderView.Interactive)
                # Столбцы дней — растягиваются на всю доступную ширину
                for c in range(2, col_count):
                    header.setSectionResizeMode(c, QHeaderView.Stretch)
        
                self.table.setColumnWidth(0, 35)
                self.table.setColumnWidth(1, 240)

        self._adjust_cell_fonts()
        self.table.verticalHeader().setVisible(False)

        # Первоначальная раскраска без ошибок (при следующем шаге
        # главное окно вызовет apply_validation и обновит цвета)
        self._paint_columns({})

        self.table.blockSignals(False)
        self.table.viewport().update()

    # ------------------------------------------------------------------
    # Валидация: фон + тултипы
    # ------------------------------------------------------------------
    def apply_validation(self, errors):
        """Перекрашивает столбцы и ставит tooltip по результатам проверки.

        errors — список словарей {"day": int, "rule": str, "message": str}
        """
        # Собираем карту: день → список строк-сообщений
        error_map = {}
        for e in errors:
            error_map.setdefault(e["day"], []).append(f"{e['rule']}: {e['message']}")

        # Блокируем сигналы, чтобы setBackground / setToolTip
        # не порождали повторный cellChanged → бесконечную рекурсию
        self.table.blockSignals(True)
        self._paint_columns(error_map)
        self.table.blockSignals(False)

        self.table.viewport().update()

    def _paint_columns(self, error_map):
        """Общий метод: применяет фон и tooltip к столбцам дней.

        error_map: {номер дня: [строки]} — только для проблемных дней.
        """
        model = self.model
        days = model.days_in_month()

        for day in range(1, days + 1):
            wd = calendar.weekday(model.year, model.month + 1, day)
            is_weekend = wd in (5, 6)
            col = day + 1

            messages = error_map.get(day, [])
            has_error = bool(messages)
            tooltip = "\n".join(messages) if has_error else ""

            if has_error:
                color = COLOR_ERROR
            elif is_weekend:
                color = COLOR_WEEKEND
            else:
                color = COLOR_WEEKDAY

            brush = QBrush(color)

            h_item = self.table.horizontalHeaderItem(col)
            if h_item is not None:
                h_item.setBackground(brush)
                h_item.setToolTip(tooltip)

            for row in range(self.table.rowCount()):
                item = self.table.item(row, col)
                if item is not None:
                    item.setBackground(brush)
                    item.setToolTip(tooltip)

    # ------------------------------------------------------------------
    def get_row_info(self, row):
        if 0 <= row < len(self.row_map):
            return self.row_map[row]
        return (None, None)
        # ------------------------------------------------------------------
    # Очистка дней (только сотрудники)
    # ------------------------------------------------------------------
    def clear_days(self, day_numbers):
        """Очищает назначения сотрудников в указанных днях (1-based).

        Для постоянных — пустая строка.
        Для совместителей:
          - рабочий код → «*» (снять рабочее место, но оставить доступность);
          - «*» → пустая строка (полностью убрать доступность);
          - пустая строка → остаётся пустой.
        Служебные строки «Э» и «О» не трогаются.
        """
        days = self.model.days_in_month()

        # 1. Обновляем модель
        for emp in self.model.employees:
            is_parttime = emp['category'] == CATEGORY_PARTTIME
            for d in day_numbers:
                idx = d - 1
                if not (0 <= idx < days):
                    continue
                current = emp["days"][idx]
                if is_parttime and current in WORKPLACE_CODES:
                    emp["days"][idx] = "*"
                else:
                    emp["days"][idx] = ""

        self.model._dirty = True

        # 2. Обновляем таблицу без сигналов — читаем актуальное значение из модели
        self.table.blockSignals(True)
        for row, (row_type, data) in enumerate(self.row_map):
            if row_type != 'employee':
                continue
            for d in day_numbers:
                col = d + 1  # 0=№, 1=ФИО, 2=день1 → колонка дня N = N+1
                idx = d - 1
                if not (0 <= idx < days):
                    continue
                item = self.table.item(row, col)
                if item is not None:
                    item.setText(data["days"][idx])
        self.table.blockSignals(False)

        # Уведомляем MainWindow: перезапуск валидации + автосохранение
        self.on_model_changed()

    # ------------------------------------------------------------------
    # Выделение столбцов
    # ------------------------------------------------------------------
    def highlight_selected_columns(self, day_numbers):
        """Подсвечивает выбранные столбцы (только ячейки дней).

        day_numbers — множество/список номеров дней (1-based).
        Пустой список — снимаем выделение.
        """
        selected = set(day_numbers)
        days = self.model.days_in_month()

        for day in range(1, days + 1):
            col = day + 1  # 0=№, 1=ФИО, 2=день1
            is_selected = day in selected

            for row in range(self.table.rowCount()):
                item = self.table.item(row, col)
                if item is None:
                    continue
                font = item.font()
                font.setBold(is_selected)
                item.setFont(font)

        self.table.viewport().update()

    def set_cell_value(self, row, col, value):
        if col < 2:
            return
        day_index = col - 2
        row_type, data = self.get_row_info(row)
        if row_type == 'employee':
            self.model.set_day(data['id'], day_index, value)
        elif row_type == 'special':
            self.model.set_special(data, day_index, value)

    def _adjust_cell_fonts(self):
        base = QFont()
        base.setPointSize(8)
        for row in range(self.table.rowCount()):
            for col in range(2, self.table.columnCount()):
                item = self.table.item(row, col)
                if item:
                    item.setFont(base)
    def on_model_changed(self):
        """Вызывается при любом изменении модели (ячейки, очистка)."""
        if self.on_change_callback:
            self.on_change_callback()  
    def get_cell_value(self, row, col):
        """Возвращает значение ячейки из модели (не из таблицы)."""
        if col < 2:
            return ""
        day_index = col - 2
        row_type, data = self.get_row_info(row)
        if row_type == 'employee':
            days = data['days']
            return days[day_index] if day_index < len(days) else ""
        elif row_type == 'special':
            values = self.model.special.get(data, [])
            return values[day_index] if day_index < len(values) else ""
        return ""           