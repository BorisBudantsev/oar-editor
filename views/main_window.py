# views/main_window.py

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QToolBar, QAction, QTableWidget,
    QComboBox, QLabel, QMessageBox, QUndoStack
)
from PyQt5.QtCore import Qt, QSize

from models.project_model import ProjectModel
from models.employee_model import EmployeeModel
from models.autosave_model import AutosaveModel
from controllers.project_controller import ProjectController
from controllers import export_controller
from controllers.undo_commands import CellEditCommand
from views.delegates import ScheduleDelegate
from views.dialogs import NewProjectWizard
from utils.constants import MONTHS
from utils import storage
from utils.validation import check_schedule


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Редактор графика ОАР")
        self.setGeometry(100, 100, 1400, 800)

        self.current_file = None
        self.selected_days = set()
        self.last_click_day = None

        # undo-стек создаём ДО _create_actions, чтобы act_undo/act_redo
        # могли ссылаться на self.undo_stack
        self.undo_stack = QUndoStack(self)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(4, 4, 4, 4)

        self._create_actions()
        self.create_menu()
        self.create_toolbar()

        # --- шапка ---
        top_panel = QHBoxLayout()
        top_panel.setSpacing(5)
        top_panel.setContentsMargins(0, 0, 0, 0)

        self.header_label = QLabel("График не создан")
        f = self.header_label.font()
        f.setBold(True)
        f.setPointSize(f.pointSize() + 1)
        self.header_label.setFont(f)
        top_panel.addWidget(self.header_label)

        top_panel.addStretch()

        top_panel.addWidget(QLabel("Масштаб:"))
        self.scale_combo = QComboBox()
        self.scale_combo.addItems(["6", "7", "8", "9", "10"])
        self.scale_combo.setCurrentIndex(2)
        top_panel.addWidget(self.scale_combo)

        main_layout.addLayout(top_panel)

        # --- таблица ---
        self.table = QTableWidget()
        main_layout.addWidget(self.table)

        # --- модель / контроллер / делегат ---
        self.project_model = ProjectModel(month=0, year=2025)
        
        self.controller = ProjectController(self.project_model, self.table)
        self.controller.on_change_callback = self._on_model_changed

        delegate = ScheduleDelegate(self.controller)
        self.table.setItemDelegate(delegate)

        # --- сигналы таблицы ---
        self.table.cellChanged.connect(self.on_cell_changed)
        self.table.cellClicked.connect(self.on_cell_clicked)
        self.table.cellClicked.connect(self._on_data_cell_clicked)

        # Контекстное меню на ячейках
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._on_table_context_menu)

        # Заголовок: клики, выделение, контекстное меню
        header = self.table.horizontalHeader()
        header.setSectionsClickable(True)
        header.sectionClicked.connect(self._on_header_clicked)
        header.setContextMenuPolicy(Qt.CustomContextMenu)
        header.customContextMenuRequested.connect(self._on_header_context_menu)

        # --- попытка восстановить автосохранение ---
        self._try_restore_autosave()

        self._update_header()
        self._update_title()

        # первичная проверка/автосохранение
        self._refresh_validation()

        self.statusBar().showMessage("Готов к работе")
        self.statusBar().setFixedHeight(25)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def _create_actions(self):
        self.act_new = QAction("Новый проект", self)
        self.act_new.setShortcut("Ctrl+N")
        self.act_new.triggered.connect(self.new_project)

        self.act_open = QAction("Открыть...", self)
        self.act_open.setShortcut("Ctrl+O")
        self.act_open.triggered.connect(self.open_project)

        self.act_save = QAction("Сохранить", self)
        self.act_save.setShortcut("Ctrl+S")
        self.act_save.triggered.connect(self.save_project)

        self.act_save_as = QAction("Сохранить как...", self)
        self.act_save_as.setShortcut("Ctrl+Shift+S")
        self.act_save_as.triggered.connect(self.save_project_as)

        self.act_exit = QAction("Выход", self)
        self.act_exit.setShortcut("Ctrl+Q")
        self.act_exit.triggered.connect(self.close)

        # --- Undo / Redo ---
        self.act_undo = QAction("Отменить", self)
        self.act_undo.setShortcut("Ctrl+Z")
        self.act_undo.triggered.connect(self.undo_stack.undo)
        self.act_undo.setEnabled(False)

        self.act_redo = QAction("Повторить", self)
        self.act_redo.setShortcut("Ctrl+Y")
        self.act_redo.triggered.connect(self.undo_stack.redo)
        self.act_redo.setEnabled(False)

        # доступность кнопок по состоянию стека
        self.undo_stack.canUndoChanged.connect(self.act_undo.setEnabled)
        self.undo_stack.canRedoChanged.connect(self.act_redo.setEnabled)

        self.act_check = QAction("Список ошибок", self)
        self.act_stats = QAction("Анализ загруженности", self)
        self.act_settings = QAction("Настройки", self)

        self.act_exp_html = QAction("HTML", self)
        self.act_exp_excel = QAction("Excel", self)
        self.act_exp_word = QAction("Word", self)
        self.act_exp_pdf = QAction("PDF", self)

        # ---- подключения, требующие уже созданных actions ----
        self.act_check.triggered.connect(self._show_errors_dialog)
        self.act_stats.triggered.connect(self._show_stats_dialog)

        self.act_exp_html.triggered.connect(self._export_html)
        self.act_exp_excel.triggered.connect(self._export_excel)
        self.act_exp_word.triggered.connect(self._export_word)
        self.act_exp_pdf.triggered.connect(self._export_pdf)

    # ------------------------------------------------------------------
    def create_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("Файл")
        file_menu.addAction(self.act_new)
        file_menu.addAction(self.act_open)
        file_menu.addAction(self.act_save)
        file_menu.addAction(self.act_save_as)
        file_menu.addSeparator()
        file_menu.addAction(self.act_exit)

        edit_menu = menubar.addMenu("Правка")
        edit_menu.addAction(self.act_undo)
        edit_menu.addAction(self.act_redo)

        tools_menu = menubar.addMenu("Инструменты")
        tools_menu.addAction(self.act_check)
        tools_menu.addAction(self.act_stats)
        tools_menu.addSeparator()
        tools_menu.addAction(self.act_settings)

        export_menu = menubar.addMenu("Экспорт")
        export_menu.addAction(self.act_exp_html)
        export_menu.addAction(self.act_exp_excel)
        export_menu.addAction(self.act_exp_word)
        export_menu.addAction(self.act_exp_pdf)

    # ------------------------------------------------------------------
    def create_toolbar(self):
        toolbar = self.addToolBar("Главная")
        toolbar.setIconSize(QSize(16, 16))

        toolbar.addAction(self.act_new)
        toolbar.addAction(self.act_open)
        toolbar.addAction(self.act_save)
        toolbar.addSeparator()
        toolbar.addAction(self.act_undo)
        toolbar.addAction(self.act_redo)
        toolbar.addSeparator()
        toolbar.addAction(self.act_stats)

    # ------------------------------------------------------------------
    # Проект: создание / открытие / сохранение
    # ------------------------------------------------------------------
    def new_project(self):
        wizard = NewProjectWizard(self)
        if wizard.exec_() == wizard.Accepted:
            month, year, employee_ids = wizard.get_result()

            new_model = ProjectModel(month=month, year=year)
            for emp_id in employee_ids:
                emp = EmployeeModel.get_by_id(emp_id)
                if emp:
                    new_model.add_employee(emp['name'], emp['category'])

            self.current_file = None
            self._apply_model(new_model)
            self.project_model.mark_clean()

            self.statusBar().showMessage(f"Создан проект: {MONTHS[month]} {year}")

    def open_project(self):
        path = storage.ask_open_path(self)
        if not path:
            return

        model, error = storage.load_model_from_file(path)
        if model is None:
            QMessageBox.critical(self, "Ошибка открытия", error)
            return

        self.current_file = path
        self._apply_model(model)
        self.project_model.mark_clean()
        AutosaveModel.clear()
        self.statusBar().showMessage(f"Открыт проект: {path}")

    def save_project(self):
        if not self.current_file:
            self.save_project_as()
            return
        if storage.save_model_to_file(self.project_model, self.current_file):
            self.project_model.mark_clean()
            AutosaveModel.clear()
            self.statusBar().showMessage(f"Сохранено: {self.current_file}")
            self._update_title()

    def save_project_as(self):
        default_name = self._default_filename()
        path = storage.ask_save_path(self, default_name)
        if not path:
            return
        if storage.save_model_to_file(self.project_model, path):
            self.current_file = path
            self.project_model.mark_clean()
            AutosaveModel.clear()
            self.statusBar().showMessage(f"Сохранено: {path}")
            self._update_title()

    # ------------------------------------------------------------------
    # Внутренние
    # ------------------------------------------------------------------
    def _apply_model(self, new_model):
        self.project_model = new_model
        self.controller = ProjectController(self.project_model, self.table)
        self.controller.on_change_callback = self._on_model_changed
        delegate = ScheduleDelegate(self.controller)
        self.table.setItemDelegate(delegate)
        self._update_header()
        self._update_title()
        self.selected_days = set()
        self.last_click_day = None
        self.undo_stack.clear()
        self._refresh_validation()

    def _update_header(self):
        m = self.project_model.month
        y = self.project_model.year
        self.header_label.setText(f"График: {MONTHS[m]} {y}")

    def _update_title(self):
        base = "Редактор графика ОАР"
        if self.current_file:
            fname = self.current_file.replace("\\", "/").split("/")[-1]
            self.setWindowTitle(f"{base} — {fname}")
        else:
            self.setWindowTitle(f"{base} — без имени")

    def _default_filename(self):
        m = self.project_model.month
        y = self.project_model.year
        return f"График_{MONTHS[m]}_{y}.json"

    # ------------------------------------------------------------------
    # Валидация и автосохранение
    # ------------------------------------------------------------------
    def _refresh_validation(self):
        errors = check_schedule(self.project_model)
        self.controller.apply_validation(errors)
        try:
            AutosaveModel.save(self.project_model.to_json())
        except Exception:
            pass

    def _on_model_changed(self):
        """Callback контроллера — вызывается при любом изменении модели."""
        self._refresh_validation()

    def _show_errors_dialog(self):
        from views.validation_dialog import ValidationDialog
        errors = check_schedule(self.project_model)
        dlg = ValidationDialog(errors, self)
        dlg.exec_()

    def _show_stats_dialog(self):
        from utils.analytics import build_report
        from views.stats_dialog import StatsDialog
        report = build_report(self.project_model)
        dlg = StatsDialog(self.project_model, report, self._get_scale(), self)
        dlg.exec_()

    # ------------------------------------------------------------------
    # Экспорт
    # ------------------------------------------------------------------
    def _get_scale(self):
        try:
            return int(self.scale_combo.currentText())
        except ValueError:
            return 8

    def _export_html(self):
        export_controller.export_html(self, self.project_model, self._get_scale())

    def _export_excel(self):
        export_controller.export_excel(self, self.project_model, self._get_scale())

    def _export_word(self):
        export_controller.export_word(self, self.project_model, self._get_scale())

    def _export_pdf(self):
        export_controller.export_pdf(self, self.project_model, self._get_scale())

    # ------------------------------------------------------------------
    # Обработчики таблицы
    # ------------------------------------------------------------------
    def on_cell_changed(self, row, col):
        """Изменение ячейки (через делегат). Кладём в undo-стек."""
        if col < 2:
            return
        item = self.table.item(row, col)
        if not item:
            return

        new_value = item.text()
        old_value = self.controller.get_cell_value(row, col)

        if new_value == old_value:
            return

        cmd = CellEditCommand(self.controller, row, col, old_value, new_value)
        self.undo_stack.push(cmd)
        self.statusBar().showMessage("Изменения сохранены")

    def on_cell_clicked(self, row, col):
        if col < 2:
            return
        item = self.table.item(row, col)
        if item:
            self.table.setFocus()
            self.table.editItem(item)

    # ------------------------------------------------------------------
    # Выделение столбцов
    # ------------------------------------------------------------------
    def _on_header_clicked(self, col):
        if col < 2:
            return
        day_num = col - 1
        days = self.project_model.days_in_month()
        if not (1 <= day_num <= days):
            return

        from PyQt5.QtWidgets import QApplication
        ctrl_pressed = bool(QApplication.keyboardModifiers() & Qt.ControlModifier)

        if ctrl_pressed and self.last_click_day is not None:
            start = min(self.last_click_day, day_num)
            end = max(self.last_click_day, day_num)
            self.selected_days = set(range(start, end + 1))
        else:
            self.selected_days = {day_num}
            self.last_click_day = day_num

        self.controller.highlight_selected_columns(self.selected_days)
        self._update_selection_status()

    def _on_data_cell_clicked(self, row, col):
        if self.selected_days:
            self.selected_days = set()
            self.last_click_day = None
            self.controller.highlight_selected_columns(self.selected_days)
            self._update_selection_status()

    def _update_selection_status(self):
        if not self.selected_days:
            self.statusBar().showMessage("Готов к работе")
            return
        days = sorted(self.selected_days)
        if len(days) == 1:
            text = f"Выделен день {days[0]}"
        elif len(days) == 2:
            text = f"Выделены дни {days[0]}, {days[1]}"
        else:
            text = f"Выделено дней: {len(days)} ({days[0]}–{days[-1]})"
        self.statusBar().showMessage(text)

    # ------------------------------------------------------------------
    # Контекстное меню на заголовке
    # ------------------------------------------------------------------
    def _on_header_context_menu(self, pos):
        from PyQt5.QtWidgets import QMenu, QMessageBox
        header = self.table.horizontalHeader()
        col = header.logicalIndexAt(pos)
        if col < 2:
            return

        day_num = col - 1
        days = self.project_model.days_in_month()
        if not (1 <= day_num <= days):
            return

        if self.selected_days and day_num in self.selected_days:
            target_days = sorted(self.selected_days)
        else:
            target_days = [day_num]

        menu = QMenu(self)
        if len(target_days) == 1:
            act_clear = menu.addAction(f"Очистить день {target_days[0]}")
        else:
            act_clear = menu.addAction(
                f"Очистить выделенные дни ({target_days[0]}–{target_days[-1]}, "
                f"всего {len(target_days)})"
            )

        chosen = menu.exec_(header.mapToGlobal(pos))
        if chosen != act_clear:
            return

        if len(target_days) == 1:
            question = f"Очистить день {target_days[0]}?"
        else:
            question = (f"Очистить {len(target_days)} дней: "
                        f"{target_days[0]}–{target_days[-1]}?")
        reply = QMessageBox.question(self, "Подтверждение", question,
                                     QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return

        self.controller.clear_days(target_days)
        self.selected_days = set()
        self.last_click_day = None
        self.controller.highlight_selected_columns(set())
        self._refresh_validation()
        self.statusBar().showMessage(f"Очищено дней: {len(target_days)}")

    # ------------------------------------------------------------------
    # Контекстное меню на ячейке данных
    # ------------------------------------------------------------------
    def _on_table_context_menu(self, pos):
        from PyQt5.QtWidgets import QMenu
        index = self.table.indexAt(pos)
        if not index.isValid():
            return

        row = index.row()
        col = index.column()

        menu = QMenu(self)
        act_copy = act_paste = act_clear = None
        if col >= 2:
            act_copy = menu.addAction("Копировать")
            act_paste = menu.addAction("Вставить")
            menu.addSeparator()
            act_clear = menu.addAction("Очистить ячейку")

        chosen = menu.exec_(self.table.viewport().mapToGlobal(pos))
        if chosen is None:
            return
        if chosen == act_copy:
            self._ctx_copy(row, col)
        elif chosen == act_paste:
            self._ctx_paste(row, col)
        elif chosen == act_clear:
            self._ctx_clear_cell(row, col)

    def _ctx_copy(self, row, col):
        from PyQt5.QtWidgets import QApplication
        item = self.table.item(row, col)
        if item:
            QApplication.clipboard().setText(item.text())
            self.statusBar().showMessage("Скопировано")

    def _ctx_paste(self, row, col):
        from PyQt5.QtWidgets import QApplication
        text = QApplication.clipboard().text().strip()
        if not text:
            return
        item = self.table.item(row, col)
        if not item:
            return

        old_value = self.controller.get_cell_value(row, col)
        if old_value == text:
            return

        cmd = CellEditCommand(self.controller, row, col, old_value, text)
        self.undo_stack.push(cmd)
        self.statusBar().showMessage("Вставлено")

    def _ctx_clear_cell(self, row, col):
        item = self.table.item(row, col)
        if not item:
            return

        old_value = self.controller.get_cell_value(row, col)
        if old_value == "":
            return

        cmd = CellEditCommand(self.controller, row, col, old_value, "")
        self.undo_stack.push(cmd)
        self.statusBar().showMessage("Ячейка очищена")

    # ------------------------------------------------------------------
    # Автосохранение
    # ------------------------------------------------------------------
    def _try_restore_autosave(self):
        data = AutosaveModel.load_latest()
        if not data:
            return

        reply = QMessageBox.question(
            self, "Восстановление",
            "Найдено автосохранение предыдущей сессии.\n"
            "Восстановить его?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        if reply == QMessageBox.Yes:
            model, error = storage.load_model_from_string(data)
            if model is None:
                QMessageBox.warning(self, "Ошибка восстановления",
                                    f"Не удалось восстановить:\n{error}")
                AutosaveModel.clear()
                return
            self.current_file = None
            self._apply_model(model)
            self.project_model.mark_clean()
            self.statusBar().showMessage("Восстановлено из автосохранения")
        else:
            AutosaveModel.clear()

    # ------------------------------------------------------------------
    # Закрытие окна
    # ------------------------------------------------------------------
    def closeEvent(self, event):
        if not self.project_model.is_dirty():
            event.accept()
            return

        reply = QMessageBox.question(
            self, "Несохранённые изменения",
            "В проекте есть несохранённые изменения.\n"
            "Сохранить перед закрытием?",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
            QMessageBox.Save
        )
        if reply == QMessageBox.Save:
            self.save_project()
            if self.project_model.is_dirty():
                event.ignore()
                return
            event.accept()
        elif reply == QMessageBox.Discard:
            event.accept()
        else:
            event.ignore()
      