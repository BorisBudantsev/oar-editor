# tests/test_duty_home.py

"""Тесты методов get_duty_home_at / set_duty_home_at в ProjectController.

Эти методы работают с флагом дежурства на дому для конкретной ячейки
таблицы. Проверяем границы: корректные строки/столбцы, граничные случаи,
игнорирование служебных строк.
"""

import pytest
from PyQt5.QtWidgets import QApplication, QTableWidget

from models.project_model import ProjectModel
from controllers.project_controller import ProjectController


@pytest.fixture(scope="module", autouse=True)
def _qapp():
    """Создаёт QApplication для всех тестов модуля."""
    app = QApplication.instance() or QApplication([])
    yield app


def _make_controller(category="permanent"):
    """Возвращает контроллер с одним сотрудником.

    row_map: [0] employee, [1] special Э, [2] special О, [3] notes
    """
    m = ProjectModel(month=0, year=2025)
    m.add_employee("Тестов", category)
    table = QTableWidget()
    controller = ProjectController(m, table)
    return controller


# ----------------------------------------------------------------------
# get_duty_home_at
# ----------------------------------------------------------------------

def test_get_duty_home_default_false():
    """По умолчанию флаг снят."""
    c = _make_controller()
    assert c.get_duty_home_at(0, 2) is False


def test_get_duty_home_after_set():
    """После установки — True."""
    c = _make_controller()
    c.set_duty_home_at(0, 2, True)
    assert c.get_duty_home_at(0, 2) is True


def test_get_duty_home_col_below_2_returns_none():
    """Для столбцов № и ФИО — None."""
    c = _make_controller()
    assert c.get_duty_home_at(0, 0) is None
    assert c.get_duty_home_at(0, 1) is None


def test_get_duty_home_special_row_returns_none():
    """Для служебных строк Э, О, notes — None."""
    c = _make_controller()
    assert c.get_duty_home_at(1, 2) is None   # Э
    assert c.get_duty_home_at(2, 2) is None   # О
    assert c.get_duty_home_at(3, 2) is None   # notes


# ----------------------------------------------------------------------
# set_duty_home_at
# ----------------------------------------------------------------------

def test_set_duty_home_changes_value():
    """Установка возвращает True и меняет флаг."""
    c = _make_controller()
    result = c.set_duty_home_at(0, 2, True)
    assert result is True
    assert c.get_duty_home_at(0, 2) is True


def test_set_duty_home_same_value_returns_false():
    """Повторная установка того же значения — False."""
    c = _make_controller()
    c.set_duty_home_at(0, 2, True)
    result = c.set_duty_home_at(0, 2, True)
    assert result is False


def test_set_duty_home_remove():
    """Снятие флага возвращает True и меняет значение."""
    c = _make_controller()
    c.set_duty_home_at(0, 2, True)
    result = c.set_duty_home_at(0, 2, False)
    assert result is True
    assert c.get_duty_home_at(0, 2) is False


def test_set_duty_home_col_below_2_returns_false():
    """Для столбцов № и ФИО — False (не меняется)."""
    c = _make_controller()
    assert c.set_duty_home_at(0, 0, True) is False
    assert c.set_duty_home_at(0, 1, True) is False


def test_set_duty_home_special_row_returns_false():
    """Для служебных строк — False."""
    c = _make_controller()
    assert c.set_duty_home_at(1, 2, True) is False   # Э
    assert c.set_duty_home_at(2, 2, True) is False   # О
    assert c.set_duty_home_at(3, 2, True) is False   # notes


def test_set_duty_home_parttime_allowed():
    """У совместителя флаг тоже работает — ограничений нет."""
    c = _make_controller("parttime")
    result = c.set_duty_home_at(0, 2, True)
    assert result is True
    assert c.get_duty_home_at(0, 2) is True