# tests/test_storage.py

import calendar
import json
import pytest

from utils.constants import PROJECT_VERSION
from utils.storage import load_model_from_string


def _valid_json(month=0, year=2025, employees=None, special=None, role="doctor",
                notes=None, duty_home_default=None):
    """Собирает корректный JSON-проект.

    duty_home_default: если передан — добавляет каждому сотруднику
    массив duty_home указанной длины (например, [False] * days).
    Если None — не добавляет поле (симулирует старый формат 2.1).
    """
    if employees is None:
        employees = []
    days = calendar.monthrange(year, month + 1)[1]
    if special is None:
        special = {"Э": ["3"] * days, "О": ["3"] * days}
    if notes is None:
        notes = [""] * days
    if duty_home_default is not None and employees:
        for emp in employees:
            if "duty_home" not in emp:
                emp["duty_home"] = list(duty_home_default)
    return json.dumps({
        "version": PROJECT_VERSION,
        "role": role,
        "month": month,
        "year": year,
        "employees": employees,
        "special": special,
        "notes": notes,
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
 # ---------------------------------------------------------------
# Проверка роли
# ---------------------------------------------------------------

def test_load_legacy_json_without_role():
    """Старый JSON без поля role считается врачебным."""
    text = _valid_json()
    data = json.loads(text)
    del data["role"]   # удаляем поле — симулируем v1.0
    model, error = load_model_from_string(json.dumps(data))
    # Роль приложения в тестах — doctor (по умолчанию), поэтому загрузка успешна
    assert error == ""
    assert model is not None
    assert model.role == "doctor"


def test_load_wrong_role_rejected():
    """JSON медсестёр не открывается в приложении врачей."""
    # Тесты запускаются с ролью doctor (по умолчанию)
    text = _valid_json(role="nurse")
    model, error = load_model_from_string(text)
    assert model is None
    assert "медицинских сестёр" in error or "врачей" in error


def test_load_correct_role_accepted():
    """JSON врачей открывается в приложении врачей."""
    text = _valid_json(role="doctor")
    model, error = load_model_from_string(text)
    assert error == ""
    assert model is not None
    assert model.role == "doctor"
    

# ---------------------------------------------------------------
# Примечания (notes)
# ---------------------------------------------------------------

def test_load_with_notes():
    """Примечания загружаются из JSON."""
    days = calendar.monthrange(2025, 1)[1]
    notes = [""] * days
    notes[3] = "отпуск"
    notes[10] = "учёба"
    text = _valid_json(notes=notes)
    model, error = load_model_from_string(text)
    assert error == ""
    assert model is not None
    assert model.notes[3] == "отпуск"
    assert model.notes[10] == "учёба"


def test_load_without_notes_legacy():
    """Файл версии 2.0 без поля notes загружается с пустыми примечаниями."""
    data = json.loads(_valid_json())
    del data["notes"]   # симулируем старый формат
    model, error = load_model_from_string(json.dumps(data))
    assert error == ""
    assert model is not None
    assert len(model.notes) == 31   # январь 2025
    assert all(x == "" for x in model.notes)


def test_load_too_short_notes():
    """Слишком короткий массив примечаний — ошибка загрузки."""
    days = calendar.monthrange(2025, 1)[1]
    text = _valid_json(notes=[""] * 5)   # 5 вместо 31
    model, error = load_model_from_string(text)
    assert model is None
    assert "notes" in error.lower() or "длина" in error.lower()


# ---------------------------------------------------------------
# Дежурство на дому (duty_home)
# ---------------------------------------------------------------

def test_load_with_duty_home():
    """duty_home загружается из JSON."""
    days = calendar.monthrange(2025, 1)[1]
    emp = {
        "id": 1, "name": "Иванов", "category": "permanent",
        "days": [""] * days,
    }
    text = _valid_json(employees=[emp], duty_home_default=[False] * days)
    # Установим флаг в исходном JSON после сборки
    data = json.loads(text)
    data["employees"][0]["duty_home"][5] = True
    data["employees"][0]["duty_home"][10] = True
    model, error = load_model_from_string(json.dumps(data))
    assert error == ""
    assert model is not None
    assert model.employees[0]["duty_home"][5] is True
    assert model.employees[0]["duty_home"][10] is True
    assert model.employees[0]["duty_home"][0] is False


def test_load_without_duty_home_legacy():
    """Файл версии 2.1 без duty_home — массив инициализируется False."""
    days = calendar.monthrange(2025, 1)[1]
    emp = {
        "id": 1, "name": "Иванов", "category": "permanent",
        "days": [""] * days,
    }
    # duty_home_default=None → поле НЕ добавляется
    text = _valid_json(employees=[emp])
    model, error = load_model_from_string(text)
    assert error == ""
    assert model is not None
    assert len(model.employees[0]["duty_home"]) == days
    assert all(x is False for x in model.employees[0]["duty_home"])


def test_load_too_short_duty_home():
    """Слишком короткий duty_home — ошибка загрузки."""
    days = calendar.monthrange(2025, 1)[1]
    emp = {
        "id": 1, "name": "Иванов", "category": "permanent",
        "days": [""] * days,
    }
    text = _valid_json(employees=[emp], duty_home_default=[False] * 5)  # 5 вместо 31
    model, error = load_model_from_string(text)
    assert model is None
    assert "duty_home" in error.lower() or "длина" in error.lower()