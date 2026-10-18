# tests/test_json_validation.py

"""Строгая валидация JSON-проекта до передачи данных остальным компонентам.

Проверяем, что повреждённый современный файл отклоняется, а не «молча
исправляется». Отдельно проверяем случай, когда длина массива верная,
но тип/значение элементов некорректны.
"""

import calendar
import json

import pytest

from utils.constants import PROJECT_VERSION
from utils.storage import load_model_from_string


DAYS = calendar.monthrange(2025, 1)[1]   # январь 2025 → 31


def _employee(emp_id=1, name="Иванов", category="permanent",
              days=None, duty_home="auto"):
    if days is None:
        days = [""] * DAYS
    emp = {"id": emp_id, "name": name, "category": category, "days": days}
    if duty_home == "auto":
        emp["duty_home"] = [False] * DAYS
    elif duty_home is not None:
        emp["duty_home"] = duty_home
    return emp


def _json(**overrides):
    """Собирает корректный JSON-проект и применяет переопределения."""
    employees = overrides.pop("employees", [])
    special = overrides.pop("special", {"Э": ["3"] * DAYS, "О": ["3"] * DAYS})
    notes = overrides.pop("notes", [""] * DAYS)
    valid_ids = [
        e.get("id") for e in employees
        if isinstance(e.get("id"), int) and not isinstance(e.get("id"), bool)
    ]
    data = {
        "version": PROJECT_VERSION,
        "role": "doctor",
        "month": 0,
        "year": 2025,
        "employees": employees,
        "special": special,
        "notes": notes,
        "nextId": (max(valid_ids) if valid_ids else 0) + 1,
    }
    data.update(overrides)
    return json.dumps(data, ensure_ascii=False)


def _load(employees=None, **overrides):
    return load_model_from_string(_json(employees=employees or [], **overrides))


# ---------------------------------------------------------------------
# Базовый успех
# ---------------------------------------------------------------------

def test_valid_modern_project_accepted():
    model, error = _load(employees=[_employee()])
    assert error == ""
    assert model is not None
    assert model.get_employee_count() == 1


# ---------------------------------------------------------------------
# month / year / nextId: bool недопустим
# ---------------------------------------------------------------------

@pytest.mark.parametrize("field, value", [
    ("month", True),
    ("month", False),
    ("year", True),
    ("nextId", True),
])
def test_bool_not_accepted_for_int_fields(field, value):
    model, error = _load(**{field: value})
    assert model is None
    assert error


def test_bool_month_message_mentions_month():
    model, error = _load(month=True)
    assert model is None
    assert "месяц" in error.lower() or "month" in error.lower()


# ---------------------------------------------------------------------
# Роль
# ---------------------------------------------------------------------

def test_role_wrong_type_rejected():
    model, error = _load(role=123)
    assert model is None
    assert "role" in error.lower()


def test_role_unknown_value_rejected():
    model, error = _load(role="admin")
    assert model is None
    assert "role" in error.lower()


def test_role_nurse_rejected_in_doctor_app():
    model, error = _load(role="nurse")
    assert model is None
    assert "медицинских сестёр" in error or "врачей" in error


# ---------------------------------------------------------------------
# Сотрудники: id
# ---------------------------------------------------------------------

@pytest.mark.parametrize("bad_id", [0, -5, "1", 1.5, True])
def test_invalid_id_rejected(bad_id):
    model, error = _load(employees=[_employee(emp_id=bad_id)])
    assert model is None


def test_duplicate_id_rejected():
    emps = [_employee(emp_id=1, name="A"), _employee(emp_id=1, name="B")]
    model, error = _load(employees=emps)
    assert model is None
    assert "id" in error.lower()


# ---------------------------------------------------------------------
# Сотрудники: name / category
# ---------------------------------------------------------------------

def test_name_wrong_type_rejected():
    model, error = _load(employees=[_employee(name=123)])
    assert model is None
    assert "name" in error.lower() or "строк" in error.lower()


def test_category_invalid_rejected():
    model, error = _load(employees=[_employee(category="other")])
    assert model is None
    assert "катег" in error.lower()


# ---------------------------------------------------------------------
# days: тип и значения
# ---------------------------------------------------------------------

def test_days_wrong_element_type_correct_length():
    """Ключевой случай: длина верная, но элемент не строка."""
    days = [""] * DAYS
    days[5] = 5
    model, error = _load(employees=[_employee(days=days)])
    assert model is None
    assert "строк" in error.lower() or "день" in error.lower()


def test_days_invalid_value_rejected():
    days = [""] * DAYS
    days[3] = "мусор"
    model, error = _load(employees=[_employee(days=days)])
    assert model is None
    assert "недопустимое" in error.lower()


def test_parttime_cannot_have_vyh():
    """У совместителя код «вых» недопустим."""
    days = [""] * DAYS
    days[0] = "вых"
    model, error = _load(employees=[_employee(category="parttime", days=days)])
    assert model is None


def test_parttime_star_allowed():
    days = [""] * DAYS
    days[0] = "*"
    model, error = _load(employees=[_employee(category="parttime", days=days)])
    assert error == ""


def test_permanent_cannot_have_star():
    days = [""] * DAYS
    days[0] = "*"
    model, error = _load(employees=[_employee(category="permanent", days=days)])
    assert model is None


# ---------------------------------------------------------------------
# special: Э и О
# ---------------------------------------------------------------------

def test_special_endo_four_rejected():
    model, error = _load(special={"Э": ["4"] * DAYS, "О": ["3"] * DAYS})
    assert model is None


def test_special_oper_five_rejected():
    model, error = _load(special={"Э": ["3"] * DAYS, "О": ["5"] * DAYS})
    assert model is None


def test_special_element_wrong_type_rejected():
    endo = ["3"] * DAYS
    endo[2] = 3
    model, error = _load(special={"Э": endo, "О": ["3"] * DAYS})
    assert model is None


def test_special_empty_string_allowed():
    endo = ["3"] * DAYS
    endo[0] = ""
    model, error = _load(special={"Э": endo, "О": ["3"] * DAYS})
    assert error == ""


# ---------------------------------------------------------------------
# notes
# ---------------------------------------------------------------------

def test_notes_wrong_element_type_rejected():
    notes = [""] * DAYS
    notes[4] = 42
    model, error = _load(notes=notes)
    assert model is None
    assert "notes" in error.lower() or "строк" in error.lower()


# ---------------------------------------------------------------------
# duty_home: строго bool
# ---------------------------------------------------------------------

@pytest.mark.parametrize("bad", [0, 1, "false", None, 1.0])
def test_duty_home_non_bool_rejected(bad):
    dh = [False] * DAYS
    dh[7] = bad
    model, error = _load(employees=[_employee(duty_home=dh)])
    assert model is None
    assert "duty_home" in error.lower() or "логическ" in error.lower()


def test_duty_home_all_bool_accepted():
    dh = [False] * DAYS
    dh[7] = True
    model, error = _load(employees=[_employee(duty_home=dh)])
    assert error == ""
    assert model.employees[0]["duty_home"][7] is True


# ---------------------------------------------------------------------
# nextId
# ---------------------------------------------------------------------

def test_next_id_not_greater_than_max_rejected():
    model, error = _load(employees=[_employee(emp_id=3)], nextId=3)
    assert model is None
    assert "nextid" in error.lower() or "согласова" in error.lower()


def test_next_id_equal_max_plus_one_accepted():
    model, error = _load(employees=[_employee(emp_id=3)], nextId=4)
    assert error == ""


def test_next_id_zero_rejected():
    model, error = _load(nextId=0)
    assert model is None


# ---------------------------------------------------------------------
# Длины массивов (сохранённая строгость)
# ---------------------------------------------------------------------

def test_days_wrong_length_rejected():
    model, error = _load(employees=[_employee(days=[""] * 5)])
    assert model is None
    assert "длина" in error.lower()


def test_special_wrong_length_rejected():
    model, error = _load(special={"Э": ["3"] * 5, "О": ["3"] * DAYS})
    assert model is None
    assert "длина" in error.lower()


def test_notes_wrong_length_rejected():
    model, error = _load(notes=[""] * 5)
    assert model is None
    assert "длина" in error.lower()


def test_duty_home_wrong_length_rejected():
    model, error = _load(employees=[_employee(duty_home=[False] * 5)])
    assert model is None
    assert "duty_home" in error.lower() or "длина" in error.lower()
