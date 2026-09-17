# views/dialogs.py

from PyQt5.QtWidgets import (
    QWizard, QWizardPage, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QSpinBox, QListWidget, QListWidgetItem,
    QPushButton, QMessageBox, QDialog, QLineEdit, QWidget,
    QCheckBox, QToolButton
)
from PyQt5.QtCore import Qt
from models.employee_model import EmployeeModel
from utils.constants import CATEGORIES, MONTHS


# ----------------------------------------------------------------------
# Виджет одного сотрудника в списке
# ----------------------------------------------------------------------
class EmployeeListItemWidget(QWidget):
    """Строка списка: [галочка] Имя (категория) #id [✎] [✕]

    show_checkbox=False — галочка скрыта (для самостоятельного справочника).
    parent_page должен иметь метод load_employees() — он вызывается после
    редактирования или удаления.
    """

    def __init__(self, emp, parent_page, show_checkbox=True):
        super().__init__()
        self.emp = emp
        self.parent_page = parent_page

        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(6)

        if show_checkbox:
            self.checkbox = QCheckBox()
            self.checkbox.setChecked(False)
            layout.addWidget(self.checkbox)
        else:
            self.checkbox = None

        label = QLabel(f"{emp['name']}  ({emp['category']})  #{emp['id']}")
        layout.addWidget(label)
        layout.addStretch()

        btn_edit = QToolButton()
        btn_edit.setText("✎")
        btn_edit.setToolTip("Редактировать сотрудника")
        btn_edit.clicked.connect(self.edit_employee)
        layout.addWidget(btn_edit)

        btn_del = QToolButton()
        btn_del.setText("✕")
        btn_del.setToolTip("Удалить сотрудника из справочника")
        btn_del.clicked.connect(self.delete_employee)
        layout.addWidget(btn_del)

    def edit_employee(self):
        dlg = AddEmployeeDialog(self, emp=self.emp)
        if dlg.exec_() != QDialog.Accepted:
            return
        name = dlg.name_edit.text().strip()
        category = dlg.category_combo.currentText()

        if not name:
            QMessageBox.information(self, "Пустое имя", "Введите имя сотрудника.")
            return
        if len(name) > 100:
            QMessageBox.warning(self, "Слишком длинное имя",
                                "Имя не должно превышать 100 символов.")
            return

        try:
            EmployeeModel.update(self.emp['id'], name, category)
            self.parent_page.load_employees()
        except Exception as e:
            QMessageBox.warning(self, "Ошибка редактирования", str(e))

    def delete_employee(self):
        reply = QMessageBox.question(
            self, "Подтверждение",
            f"Удалить сотрудника «{self.emp['name']}» из справочника?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            EmployeeModel.delete(self.emp['id'])
            self.parent_page.load_employees()

# ----------------------------------------------------------------------
# Мастер создания нового проекта
# ----------------------------------------------------------------------
class NewProjectWizard(QWizard):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Создание нового графика")
        self.setWizardStyle(QWizard.ModernStyle)

        # Сохраняем ссылки на страницы (обращаемся к ним напрямую)
        self.page_month = PageMonthYear()
        self.page_employees = PageEmployees()

        # Добавляем страницы в мастер
        self.addPage(self.page_month)
        self.addPage(self.page_employees)

        self.setButtonText(QWizard.FinishButton, "Создать")
        self.setButtonText(QWizard.CancelButton, "Отмена")

    def get_result(self):
        """Возвращает (month, year, [employee_ids])."""
        month = self.page_month.month_combo.currentIndex()
        year = self.page_month.year_spin.value()
        employee_ids = self.page_employees.get_checked_ids()
        return month, year, employee_ids


# ----------------------------------------------------------------------
# Страница 1: выбор месяца и года
# ----------------------------------------------------------------------
class PageMonthYear(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Выберите месяц и год")
        self.setSubTitle("Укажите месяц и год для нового графика.")

        layout = QVBoxLayout(self)

        # Месяц
        m = QHBoxLayout()
        m.addWidget(QLabel("Месяц:"))
        self.month_combo = QComboBox()
        self.month_combo.addItems(MONTHS)
        self.month_combo.setCurrentIndex(0)
        m.addWidget(self.month_combo)
        layout.addLayout(m)

        # Год
        y = QHBoxLayout()
        y.addWidget(QLabel("Год:"))
        self.year_spin = QSpinBox()
        self.year_spin.setRange(2000, 2100)
        self.year_spin.setValue(2025)
        y.addWidget(self.year_spin)
        layout.addLayout(y)

        layout.addStretch()


# ----------------------------------------------------------------------
# Страница 2: выбор сотрудников
# ----------------------------------------------------------------------
class PageEmployees(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Выберите сотрудников")
        self.setSubTitle("Отметьте галочками тех, кто должен попасть в график.")

        layout = QVBoxLayout(self)

        # Список — отключаем выделение фоном
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.NoSelection)
        layout.addWidget(self.list_widget)

        # Кнопка добавления нового сотрудника
        self.add_btn = QPushButton("Добавить сотрудника")
        self.add_btn.clicked.connect(self.add_employee)
        layout.addWidget(self.add_btn)

        self.load_employees()

    def load_employees(self):
        """Загружает список сотрудников из БД и создаёт для каждого виджет-строку."""
        self.list_widget.clear()
        for emp in EmployeeModel.get_all():
            item = QListWidgetItem(self.list_widget)
            widget = EmployeeListItemWidget(emp, self)
            item.setSizeHint(widget.sizeHint())
            self.list_widget.setItemWidget(item, widget)

    def get_checked_ids(self):
        """Возвращает ID только отмеченных галочками сотрудников."""
        ids = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            widget = self.list_widget.itemWidget(item)
            if widget and widget.checkbox.isChecked():
                ids.append(widget.emp['id'])
        return ids

    def add_employee(self):
        """Открывает диалог добавления сотрудника."""
        dialog = AddEmployeeDialog(self)
        if dialog.exec_() != QDialog.Accepted:
            return

        name = dialog.name_edit.text().strip()
        category = dialog.category_combo.currentText()

        # Проверка на пустое имя
        if not name:
            QMessageBox.information(self, "Пустое имя",
                                    "Введите имя сотрудника.")
            return

        # Проверка на слишком длинное имя (защита от случайной вставки)
        if len(name) > 100:
            QMessageBox.warning(self, "Слишком длинное имя",
                                "Имя не должно превышать 100 символов.")
            return

        # Дубликаты теперь разрешены — БД не выдаст IntegrityError.
        try:
            EmployeeModel.add(name, category)
            self.load_employees()
        except Exception as e:
            QMessageBox.warning(self, "Ошибка добавления", str(e))


# ----------------------------------------------------------------------
# Диалог добавления нового сотрудника
class AddEmployeeDialog(QDialog):
    """Диалог добавления или редактирования сотрудника.

    Если emp передан — режим редактирования (поля предзаполнены).
    """

    def __init__(self, parent=None, emp=None):
        super().__init__(parent)
        self.setWindowTitle("Редактировать сотрудника" if emp else "Добавить сотрудника")
        self.setModal(True)

        layout = QVBoxLayout(self)

        h1 = QHBoxLayout()
        h1.addWidget(QLabel("Имя:"))
        self.name_edit = QLineEdit()
        h1.addWidget(self.name_edit)
        layout.addLayout(h1)

        h2 = QHBoxLayout()
        h2.addWidget(QLabel("Категория:"))
        self.category_combo = QComboBox()
        self.category_combo.addItems(CATEGORIES)
        h2.addWidget(self.category_combo)
        layout.addLayout(h2)

        if emp:
            self.name_edit.setText(emp['name'])
            idx = self.category_combo.findText(emp['category'])
            if idx >= 0:
                self.category_combo.setCurrentIndex(idx)

        btns = QHBoxLayout()
        ok = QPushButton("OK")
        ok.clicked.connect(self.accept)
        cancel = QPushButton("Отмена")
        cancel.clicked.connect(self.reject)
        btns.addWidget(ok)
        btns.addWidget(cancel)
        layout.addLayout(btns)# ----------------------------------------------------------------------
class EmployeeDirectoryDialog(QDialog):
    """Самостоятельный справочник сотрудников.

    Открывается из главного меню без создания нового проекта.
    Изменения применяются только к новым проектам — существующие
    проекты не обновляются автоматически.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Справочник сотрудников")
        self.setModal(True)
        self.resize(560, 560)

        layout = QVBoxLayout(self)

        info = QLabel(
            "Изменения в справочнике применяются только к новым проектам.\n"
            "Ранее созданные проекты сохраняют состав и категории на момент создания."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #555; padding: 4px;")
        layout.addWidget(info)

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.NoSelection)
        layout.addWidget(self.list_widget)

        btn_row = QHBoxLayout()

        self.add_btn = QPushButton("Добавить сотрудника")
        self.add_btn.clicked.connect(self.add_employee)
        btn_row.addWidget(self.add_btn)
        btn_row.addStretch()

        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)

        layout.addLayout(btn_row)

        self.load_employees()

    def load_employees(self):
        self.list_widget.clear()
        for emp in EmployeeModel.get_all():
            item = QListWidgetItem(self.list_widget)
            widget = EmployeeListItemWidget(emp, self, show_checkbox=False)
            item.setSizeHint(widget.sizeHint())
            self.list_widget.setItemWidget(item, widget)

    def add_employee(self):
        dlg = AddEmployeeDialog(self)
        if dlg.exec_() != QDialog.Accepted:
            return

        name = dlg.name_edit.text().strip()
        category = dlg.category_combo.currentText()

        if not name:
            QMessageBox.information(self, "Пустое имя", "Введите имя сотрудника.")
            return
        if len(name) > 100:
            QMessageBox.warning(self, "Слишком длинное имя",
                                "Имя не должно превышать 100 символов.")
            return

        try:
            EmployeeModel.add(name, category)
            self.load_employees()
        except Exception as e:
            QMessageBox.warning(self, "Ошибка добавления", str(e))