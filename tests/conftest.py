# tests/conftest.py

import pytest
from models.project_model import ProjectModel


@pytest.fixture
def model():
    """Пустая модель: январь 2025, 31 день, Э=О=«3», сотрудников нет."""
    return ProjectModel(month=0, year=2025)


@pytest.fixture
def filled_day_model():
    """Модель с корректно заполненным первым днём.

    Э=3, О=3 → работающих 7: З, Б, Ж, ЭНД1, ЭНД2, ЭНД3, Д.
    """
    m = ProjectModel(month=0, year=2025)
    codes = ["З", "Б", "Ж", "ЭНД1", "ЭНД2", "ЭНД3", "Д"]
    for i, code in enumerate(codes):
        m.add_employee(f"Emp{i}", "permanent")
        m.employees[-1]["days"][0] = code
    return m