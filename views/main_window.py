# views/main_window.py

import logging
import os

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QToolBar, QAction, QTableWidget,
    QComboBox, QLabel, QMessageBox, QUndoStack
)
from PyQt5.QtCore import Qt, QSize, QTimer
from PyQt5.QtGui import QIcon

from models.project_model import ProjectModel
from models.employee_model import EmployeeModel
from models.autosave_model import AutosaveModel
from controllers.project_controller import ProjectController
from controllers import export_controller
from controllers.undo_commands import CellEditCommand, DutyHomeCommand
from views.delegates import ScheduleDelegate
from views.dialogs import NewProjectWizard
from utils.constants import MONTHS
from utils import storage
from utils.resources import resource_path
from utils.validation import check_schedule
from utils.logger import get_log_path
from app_config import get


logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Редактор графика ОАР")
        self.setGeometry(100, 100, 1400, 800)

        self.current_file = None
        self.selected_days = set()
        self.last_click_day = None
        self._project_loaded = False

        # undo-стек создаём ДО _create_actions, чтобы act_undo/act_redo
        # могли ссылаться на self.undo_stack
        self.undo_stack = QUndoStack(self)
        self._autosave_timer = QTimer(self)
        self._autosave_timer.setSingleShot(True)
        self._autosave_timer.setInterval(1500)
        self._autosave_timer.timeout.connect(self._do_autosave)

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
        header.setContextMenuPolicy(Qt.NoContextMenu)

        # --- попытка восстановить автосохранение ---
        self._try_restore_autosave()

        self._update_header()
        self._update_title()

             # первичная проверка — только если проект уже загружен
        # (создан, открыт или восстановлен из автосейва)
        if self._project_loaded:
            self._refresh_validation()

        log_path = get_log_path()
        self.statusBar().showMessage(f"Готов к работе. Лог: {log_path}")
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
        self.act_directory = QAction("Справочник сотрудников", self)
        self.act_directory.triggered.connect(self._show_directory_dialog)
        self.act_open_logs = QAction("Открыть папку с логами", self)
        self.act_open_logs.triggered.connect(self._open_logs_folder)

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

        self._assign_icons()

    # ------------------------------------------------------------------
    # Иконки действий
    # ------------------------------------------------------------------
    def _assign_icons(self):
        """Назначает иконки действиям панели инструментов и меню.

        Иконки берутся из `assets/icons/`. Файл намеренно указывается явно
        (а не через набор стандартных иконок Qt), чтобы оформление не
        зависело от системной темы.
        """
        icons = {
            self.act_new: "new",
            self.act_open: "open",
            self.act_save: "save",
            self.act_save_as: "save_as",
            self.act_exit: "exit",
            self.act_undo: "undo",
            self.act_redo: "redo",
            self.act_check: "check",
            self.act_stats: "stats",
            self.act_directory: "directory",
            self.act_open_logs: "open_logs",
            self.act_exp_html: "export_html",
            self.act_exp_excel: "export_excel",
            self.act_exp_word: "export_word",
            self.act_exp_pdf: "export_pdf",
        }
        for action, name in icons.items():
            icon = self._icon(name)
            if not icon.isNull():
                action.setIcon(icon)

    @staticmethod
    def _icon(name):
        """Возвращает QIcon из `assets/icons/<name>.svg` (пустой, если нет файла)."""
        path = resource_path(os.path.join("assets", "icons", name + ".svg"))
        if os.path.exists(path):
            return QIcon(path)
        logger.warning("Иконка не найдена: %s", path)
        return QIcon()

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
        tools_menu.addAction(self.act_directory)
        tools_menu.addSeparator()
        tools_menu.addAction(self.act_open_logs)

        export_menu = menubar.addMenu("Экспорт")
        export_menu.addAction(self.act_exp_html)
        export_menu.addAction(self.act_exp_excel)
        export_menu.addAction(self.act_exp_word)
        export_menu.addAction(self.act_exp_pdf)

    # ------------------------------------------------------------------
    def create_toolbar(self):
        toolbar = self.addToolBar("Главная")
        toolbar.setIconSize(QSize(24, 24))

        # Файл
        toolbar.addAction(self.act_new)
        toolbar.addAction(self.act_open)
        toolbar.addAction(self.act_save)
        toolbar.addAction(self.act_save_as)
        toolbar.addAction(self.act_exit)
        toolbar.addSeparator()

        # Правка
        toolbar.addAction(self.act_undo)
        toolbar.addAction(self.act_redo)
        toolbar.addSeparator()

        # Инструменты
        toolbar.addAction(self.act_check)
        toolbar.addAction(self.act_stats)
        toolbar.addAction(self.act_directory)
        toolbar.addAction(self.act_open_logs)
        toolbar.addSeparator()

        # Экспорт
        toolbar.addAction(self.act_exp_html)
        toolbar.addAction(self.act_exp_excel)
        toolbar.addAction(self.act_exp_word)
        toolbar.addAction(self.act_exp_pdf)

    # ------------------------------------------------------------------
    # Проект: создание / открытие / сохранение
    # ------------------------------------------------------------------
    def new_project(self):
        """Создаёт новый проект через мастер.

        Мастер показывается РАНЬШЕ вопроса о несохранённых изменениях.
        Если пользователь отменит мастер, текущий проект, его файл и
        автосохранение остаются нетронутыми. Вопрос о судьбе текущего
        проекта задаётся только после того, как создание подтверждено.
        """
        wizard = NewProjectWizard(self)
        if wizard.exec_() != wizard.Accepted:
            # Отмена мастера — ничего не меняем и не трогаем автосохранение.
            return

        month, year, employee_ids = wizard.get_result()

        # Создание подтверждено — только теперь решаем судьбу текущего проекта.
        if not self._maybe_save_changes():
            return

        new_model = ProjectModel(month=month, year=year)
        for emp_id in employee_ids:
            emp = EmployeeModel.get_by_id(emp_id)
            if emp:
                new_model.add_employee(emp['name'], emp['category'])

        self.current_file = None
        self._apply_model(new_model)
        # Новый проект без файла считается несохранённым даже без правок,
        # поэтому НЕ помечаем его «чистым».

        self.statusBar().showMessage(f"Создан проект: {MONTHS[month]} {year}")

    def open_project(self):
        """Открывает проект из файла.

        Файл выбирается и загружается РАНЬШЕ вопроса о несохранённых
        изменениях. Поэтому отмена выбора файла, ошибка чтения/валидации
        и отмена в диалоге сохранения не затрагивают текущий проект, его
        файл и автосохранение: переключение просто не выполняется.
        """
        path = storage.ask_open_path(self)
        if not path:
            # Отмена выбора файла — текущий проект не трогаем.
            return

        model, error = storage.load_model_from_file(path)
        if model is None:
            # Файл не загрузился — исходный проект и автосохранение целы.
            QMessageBox.critical(self, "Ошибка открытия", error)
            return

        # Новый файл успешно прочитан и провалидирован. Только теперь
        # спрашиваем о судьбе несохранённых изменений текущего проекта:
        # «Сохранить» запишет старый проект, «Не сохранять» отбросит его,
        # «Отмена» оставит всё как есть.
        if not self._maybe_save_changes():
            return

        self.current_file = path
        self._apply_model(model)
        self.project_model.mark_clean()
        # Файл только что открыт и не изменялся — автосохранение не нужно,
        # иначе при следующем запуске появится ложное предложение восстановить.
        self._clear_autosave()
        self.statusBar().showMessage(f"Открыт проект: {path}")

    def save_project(self):
        """Сохраняет проект. Возвращает True только при реальном успехе."""
        if not self.current_file:
            return self.save_project_as()
        return self._save_to(self.current_file)

    def save_project_as(self):
        """Сохраняет проект под новым именем. Возвращает True при успехе."""
        default_name = self._default_filename()
        path = storage.ask_save_path(self, default_name)
        if not path:
            # Пользователь отменил выбор файла — текущий проект не меняем.
            return False
        return self._save_to(path)

    def _save_to(self, path):
        """Пишет модель в файл. При успехе сбрасывает «грязное» состояние.

        При ошибке записи текущий проект и текущий файл не меняются.
        """
        if not storage.save_model_to_file(self.project_model, path):
            return False
        self.current_file = path
        self.project_model.mark_clean()
        # Контрольная точка отмены совпадает с состоянием файла.
        self.undo_stack.setClean()
        # Сохранённая версия теперь в файле — отложенный автосейв не нужен,
        # иначе таймер воскресит запись после успешного сохранения.
        self._clear_autosave()
        self.statusBar().showMessage(f"Сохранено: {path}")
        self._update_title()
        return True

    # ------------------------------------------------------------------
    # Внутренние
    # ------------------------------------------------------------------
    def _apply_model(self, new_model):
        # Гасим отложенный автосейв предыдущего проекта, чтобы он не сработал
        # уже на новом проекте.
        self._autosave_timer.stop()
        self._project_loaded = True
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
        # Немедленный автосейв - чтобы только что созданный/открытый
        # восстановленный проект сразу попал в БД и не потерялся
        self._do_autosave()

    def _update_header(self):
        if not self._project_loaded:
            self.header_label.setText(get("empty_state"))
            return
        m = self.project_model.month
        y = self.project_model.year
        self.header_label.setText(f"{get('app_title')}: {MONTHS[m]} {y}") 

    def _update_title(self):
        base = get("app_title")
        if not self._project_loaded:
            self.setWindowTitle(base)
            return
        if self.current_file:
            fname = self.current_file.replace("\\", "/").split("/")[-1]
            self.setWindowTitle(f"{base} — {fname}")
        else:
            self.setWindowTitle(f"{base} — без имени")   
    def _default_filename(self):
        m = self.project_model.month
        y = self.project_model.year
        return get("project_filename").format(month=MONTHS[m], year=y)
    
    def _clear_autosave(self):
        """Гасит отложенный таймер и удаляет запись автосохранения."""
        self._autosave_timer.stop()
        try:
            AutosaveModel.clear()
        except Exception:
            logger.exception("Ошибка очистки автосохранения")

    def _has_unsaved_changes(self):
        """Есть ли в текущем проекте несохранённые изменения.

        Учитываются два случая:
          - проект без файла считается несохранённым всегда (новая работа);
          - иначе — расхождение контрольной точки стека отмены с текущим
            состоянием (после полного Undo состояние снова «чистое»).

        ВАЖНО (условие корректности): определение опирается только на
        QUndoStack и НЕ использует флаг модели ``_dirty``. Это осознанно:
        после полного Undo данные могут совпадать с сохранёнными, хотя
        ``_dirty`` остаётся истинным (наивная комбинация
        ``isClean() and not is_dirty()`` дала бы неверный результат).

        Следовательно, любое действие пользователя, меняющее данные проекта,
        обязано проходить через undo-стек (``CellEditCommand`` /
        ``DutyHomeCommand``), иначе изменение не будет обнаружено. Сегодня
        так и есть: ``ProjectController.set_cell_value`` и
        ``set_duty_home_at`` вызываются только из undo-команд, а правки
        ячеек делегатом идут через ``cellChanged`` → ``on_cell_changed``.
        При добавлении операций вне стека (например, массовой вставки)
        нужно либо заворачивать их в команду, либо двигать контрольную
        точку ``undo_stack.setClean()``.
        """
        if not self._project_loaded:
            return False
        if not self.current_file:
            return True
        return not self.undo_stack.isClean()

    def _maybe_save_changes(self):
        """Единая проверка перед закрытием или заменой текущего проекта.

        Возвращает True, если продолжать можно (изменений нет, либо
        пользователь сохранил, либо отказался от них). False — отмена.
        """
        if not self._has_unsaved_changes():
            return True

        reply = QMessageBox.question(
            self, "Несохранённые изменения",
            "В проекте есть несохранённые изменения.\n"
            "Сохранить их перед продолжением?",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
            QMessageBox.Save
        )
        if reply == QMessageBox.Save:
            # Успех сохранения — единственный признак, что можно продолжать.
            return self.save_project()
        if reply == QMessageBox.Discard:
            # Явный отказ от изменений — автосохранение не должно
            # предлагаться к восстановлению при следующем запуске.
            self._clear_autosave()
            return True
        return False

    def _do_autosave(self):
        """Реальное сохранение в SQLite. Вызывается по таймеру или принудительно."""
        try:
            AutosaveModel.save(self.project_model.to_json())
        except Exception:
            logger.exception("Ошибка автосохранения проекта")

       # Валидация и автосохранение
    # ------------------------------------------------------------------
    def _refresh_validation(self):
        errors = check_schedule(self.project_model)
        self.controller.apply_validation(errors)
 

    def _on_model_changed(self):
        """Callback контроллера — вызывается при любом изменении модели."""
        self._refresh_validation()
        self._autosave_timer.start()

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
        
    def _show_directory_dialog(self):
        from views.dialogs import EmployeeDirectoryDialog
        dlg = EmployeeDirectoryDialog(self)
        dlg.exec_()

    def _open_logs_folder(self):
        """Открывает папку с логами в Проводнике."""
        import os
        import subprocess

        path = get_log_path()
        folder = os.path.dirname(path)
        try:
            if os.path.exists(folder):
                # Windows
                os.startfile(folder)
            else:
                QMessageBox.information(
                    self, "Папка логов",
                    f"Папка ещё не создана:\n{folder}"
                )
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось открыть папку:\n{e}")

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
        act_copy = act_paste = None
        act_duty_on = act_duty_off = None

        if col >= 2:
            act_copy = menu.addAction("Копировать")
            act_paste = menu.addAction("Вставить")

            row_type, _ = self.controller.get_row_info(row)
            if row_type == 'employee':
                menu.addSeparator()
                current_flag = self.controller.get_duty_home_at(row, col)
                act_duty_on = menu.addAction("Дежурство на дому")
                act_duty_off = menu.addAction("Убрать дежурство на дому")
                act_duty_on.setEnabled(not current_flag)
                act_duty_off.setEnabled(bool(current_flag))

        chosen = menu.exec_(self.table.viewport().mapToGlobal(pos))
        if chosen is None:
            return
        if chosen == act_copy:
            self._ctx_copy(row, col)
        elif chosen == act_paste:
            self._ctx_paste(row, col)
        elif chosen == act_duty_on:
            self._ctx_set_duty(row, col, True)
        elif chosen == act_duty_off:
            self._ctx_set_duty(row, col, False)

    def _ctx_copy(self, row, col):
        from PyQt5.QtWidgets import QApplication
        item = self.table.item(row, col)
        if item:
            QApplication.clipboard().setText(item.text())
            self.statusBar().showMessage("Скопировано")

    def _ctx_paste(self, row, col):
        from PyQt5.QtWidgets import QApplication
        from utils.rules import allowed_values, allowed_special_values

        text = QApplication.clipboard().text().strip()
        if not text:
            return
        item = self.table.item(row, col)
        if not item:
            return

        row_type, data = self.controller.get_row_info(row)

        if row_type == 'employee':
            current = self.controller.get_cell_value(row, col)
            allowed = set(allowed_values(data, current))
        elif row_type == 'special':
            allowed = set(allowed_special_values(data))
        else:
            return

        if text not in allowed:
            self.statusBar().showMessage(
                f"Недопустимое значение для вставки: «{text}»"
            )
            return

        old_value = self.controller.get_cell_value(row, col)
        if old_value == text:
            return

        cmd = CellEditCommand(self.controller, row, col, old_value, text)
        self.undo_stack.push(cmd)
        self.statusBar().showMessage("Вставлено")
        
    def _ctx_set_duty(self, row, col, value):
        """Устанавливает или снимает флаг дежурства на дому через undo-стек."""
        old = self.controller.get_duty_home_at(row, col)
        if old is None or old == value:
            return
        cmd = DutyHomeCommand(self.controller, row, col, old, value)
        self.undo_stack.push(cmd)
        if value:
            self.statusBar().showMessage("Дежурство на дому отмечено")
        else:
            self.statusBar().showMessage("Дежурство на дому снято")
        
    
    # ------------------------------------------------------------------
    # Автосохранение
    # ------------------------------------------------------------------
    def _try_restore_autosave(self):
        try:
            data = AutosaveModel.load_latest()
        except Exception:
            # Повреждена или недоступна БД автосохранения — приложение
            # должно продолжать работу, а не падать.
            logger.exception("Ошибка чтения автосохранения")
            QMessageBox.warning(
                self, "Восстановление",
                "Не удалось прочитать автосохранение предыдущей сессии.\n"
                "Приложение продолжит работу без восстановления."
            )
            return
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
        # Единый механизм: нет изменений — закрываем; есть — спрашиваем.
        if not self._maybe_save_changes():
            event.ignore()
            return

        # Нормальное завершение работы: автосохранение не нужно, иначе
        # при следующем запуске появится ложное сообщение о восстановлении.
        # При аварийном завершении (closeEvent не вызывается) запись остаётся.
        self._clear_autosave()
        event.accept()