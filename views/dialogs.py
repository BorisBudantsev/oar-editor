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
    """Строка списка: [галочка] Имя (категория) [✕]"""
    def __init__(self, emp, parent_page):
        super().__init__()
        self.emp = emp
        self.parent_page = parent_page

        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(6)

        # Галочка выбора
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(False)
        layout.addWidget(self.checkbox)

        # Имя и категория
                # Имя, категория и ID (для отличия дубликатов)
        label = QLabel(f"{emp['name']}  ({emp['category']})  #{emp['id']}")
        layout.addWidget(label)
        layout.addStretch()

        # Крестик удаления
        btn_del = QToolButton()
        btn_del.setText("✕")
        btn_del.setToolTip("Удалить сотрудника из справочника")
        btn_del.clicked.connect(self.delete_employee)
        layout.addWidget(btn_del)

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
# ----------------------------------------------------------------------
class AddEmployeeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Добавить сотрудника")
        self.setModal(True)

        layout = QVBoxLayout(self)

        # Имя
        h1 = QHBoxLayout()
        h1.addWidget(QLabel("Имя:"))
        self.name_edit = QLineEdit()
        h1.addWidget(self.name_edit)
        layout.addLayout(h1)

        # Категория
        h2 = QHBoxLayout()
        h2.addWidget(QLabel("Категория:"))
        self.category_combo = QComboBox()
        self.category_combo.addItems(CATEGORIES)
        h2.addWidget(self.category_combo)
        layout.addLayout(h2)

        # Кнопки OK / Отмена
        btns = QHBoxLayout()
        ok = QPushButton("OK")
        ok.clicked.connect(self.accept)
        cancel = QPushButton("Отмена")
        cancel.clicked.connect(self.reject)
        btns.addWidget(ok)
        btns.addWidget(cancel)
        layout.addLayout(btns)