# tests/test_storage.py

import calendar
import json
import pytest

from utils.constants import PROJECT_VERSION
from utils.storage import load_model_from_string


def _valid_json(month=0, year=2025, employees=None, special=None):
    """Собирает корректный JSON-проект."""
    if employees is None:
        employees = []
    if special is None:
        days = calendar.monthrange(year, month + 1)[1]
        special = {"Э": ["3"] * days, "О": ["3"] * days}
    return json.dumps({
        "version": PROJECT_VERSION,
        "month": month,
        "year": year,
        "employees": employees,
        "special": special,
        "nextId": 1,
    }, ensure_ascii=False)


# ---------------------------------------------------------------
# Успешная загрузка
# ---------------------------------------------------------------

def test_load_valid_project():
    text = _valid_json()
    model, error = load_model_from_string(text)
    assert error == ""
    assert model is not None
    assert model.month == 0
    assert model.year == 2025


# ---------------------------------------------------------------
# Битый JSON
# ---------------------------------------------------------------

def test_load_broken_json():
    model, error = load_model_from_string("{ not valid json")
    assert model is None
    assert "JSON" in error or "поврежд" in error.lower()


def test_load_non_object_json():
    model, error = load_model_from_string("[1, 2, 3]")
    assert model is None
    assert "структура" in error.lower() or "объект" in error.lower()


# ---------------------------------------------------------------
# Несовместимая версия
# ---------------------------------------------------------------

def test_load_wrong_version():
    data = json.loads(_valid_json())
    data["version"] = "99.0"
    model, error = load_model_from_string(json.dumps(data))
    assert model is None
    assert "версия" in error.lower() or "version" in error.lower()


# ---------------------------------------------------------------
# Отсутствующие поля
# ---------------------------------------------------------------

def test_load_missing_field():
    data = json.loads(_valid_json())
    del data["month"]
    model, error = load_model_from_string(json.dumps(data))
    assert model is None
    assert "поля" in error.lower() or "month" in error


# ---------------------------------------------------------------
# Неверные значения
# ---------------------------------------------------------------

def test_load_invalid_month():
    data = json.loads(_valid_json())
    data["month"] = 42
    model, error = load_model_from_string(json.dumps(data))
    assert model is None
    assert "месяц" in error.lower()


def test_load_invalid_year():
    data = json.loads(_valid_json())
    data["year"] = 1000
    model, error = load_model_from_string(json.dumps(data))
    assert model is None
    assert "год" in error.lower()


# ---------------------------------------------------------------
# Повреждённая длина days / special (строгая валидация)
# ---------------------------------------------------------------

def test_load_too_short_days():
    emp = {"id": 1, "name": "Иванов", "category": "permanent",
           "days": [""] * 5}
    text = _valid_json(employees=[emp])
    model, error = load_model_from_string(text)
    assert model is None
    assert "длина" in error.lower()


def test_load_too_short_special():
    days = calendar.monthrange(2025, 1)[1]
    text = _valid_json(special={"Э": ["3"] * 5, "О": ["3"] * days})
    model, error = load_model_from_string(text)
    assert model is None
    assert "длина" in error.lower()


# ---------------------------------------------------------------
# Минимально валидный проект с сотрудником
# ---------------------------------------------------------------

def test_load_project_with_employee():
    days = calendar.monthrange(2025, 1)[1]
    emp = {"id": 1, "name": "Иванов И.И.", "category": "permanent",
           "days": [""] * days}
    text = _valid_json(employees=[emp])
    model, error = load_model_from_string(text)
    assert error == ""
    assert model.get_employee_count() == 1
    assert model.employees[0]["name"] == "Иванов И.И."