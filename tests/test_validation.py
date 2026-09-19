# tests/test_validation.py

from models.project_model import ProjectModel
from utils.validation import check_day, check_schedule


# ---------------------------------------------------------------
# Пустой / корректный день
# ---------------------------------------------------------------

def test_empty_day_has_errors(model):
    """Пустой день: нет работающих, нет дежурного."""
    errors = check_day(model, 0)
    rules = [e["rule"] for e in errors]
    assert "Работающие" in rules
    assert "Дежурный" in rules


def test_full_working_day_ok(filled_day_model):
    """Корректно заполненный день не даёт ошибок."""
    errors = check_day(filled_day_model, 0)
    assert errors == []


def test_check_schedule_scans_all_days(model):
    """check_schedule проверяет все дни месяца (31 в январе)."""
    errors = check_schedule(model)
    days = set(e["day"] for e in errors)
    # Должны быть ошибки по каждому дню месяца
    assert days == set(range(1, 32))


# ---------------------------------------------------------------
# Недопустимые значения
# ---------------------------------------------------------------

def test_permanent_with_star_error(model):
    """У постоянного символ «*» — недопустимое значение."""
    model.add_employee("Иванов", "permanent")
    model.employees[0]["days"][0] = "*"
    errors = check_day(model, 0)
    value_errors = [e for e in errors if e["rule"] == "Значение"]
    assert len(value_errors) == 1
    assert "Иванов" in value_errors[0]["message"]


def test_invalid_garbage_value(model):
    """Произвольный текст — ошибка значения."""
    model.add_employee("Иванов", "permanent")
    model.employees[0]["days"][0] = "мусор"
    errors = check_day(model, 0)
    value_errors = [e for e in errors if e["rule"] == "Значение"]
    assert len(value_errors) == 1


# ---------------------------------------------------------------
# Служебные строки Э и О
# ---------------------------------------------------------------

def test_empty_special_rows_error(model):
    """Пустые служебные строки Э и О — две ошибки."""
    model.set_special("Э", 0, "")
    model.set_special("О", 0, "")
    errors = check_day(model, 0)
    rules = [e["rule"] for e in errors]
    assert "Места Э" in rules
    assert "Места О" in rules


def test_special_invalid_value(model):
    """Недопустимое значение в служебной строке — ошибка."""
    model.set_special("Э", 0, "9")
    errors = check_day(model, 0)
    rules = [e["rule"] for e in errors]
    assert "Места Э" in rules


# ---------------------------------------------------------------
# Дежурный
# ---------------------------------------------------------------

def test_no_duty_error(model):
    """Ни одного «Д» — ошибка «Отсутствует дежурный»."""
    model.add_employee("Иванов", "permanent")
    model.employees[0]["days"][0] = "З"
    errors = check_day(model, 0)
    duty_errors = [e for e in errors if e["rule"] == "Дежурный"]
    assert len(duty_errors) == 1
    assert "Отсутствует" in duty_errors[0]["message"]


def test_two_duties_error(model):
    """Два «Д» — ошибка «Дежурных 2, должен быть один»."""
    codes = ["З", "Б", "Ж", "ЭНД1", "ЭНД2", "Д", "Д"]
    for i, code in enumerate(codes):
        model.add_employee(f"Emp{i}", "permanent")
        model.employees[-1]["days"][0] = code
    errors = check_day(model, 0)
    duty_errors = [e for e in errors if e["rule"] == "Дежурный"]
    assert len(duty_errors) == 1
    assert "2" in duty_errors[0]["message"]


# ---------------------------------------------------------------
# Число работающих
# ---------------------------------------------------------------

def test_workers_count_mismatch(model):
    """Меньше работающих, чем Э + О + 1."""
    for i, code in enumerate(["З", "Б", "Д"]):   # 3 работающих вместо 7
        model.add_employee(f"Emp{i}", "permanent")
        model.employees[-1]["days"][0] = code
    errors = check_day(model, 0)
    worker_errors = [e for e in errors if e["rule"] == "Работающие"]
    assert len(worker_errors) == 1
    assert "3" in worker_errors[0]["message"]
    assert "7" in worker_errors[0]["message"]


# ---------------------------------------------------------------
# Дубликаты мест
# ---------------------------------------------------------------

def test_duplicate_workplace_error(model):
    """Два человека на «З» — ошибка «Место «З»»."""
    codes = ["З", "З", "Ж", "ЭНД1", "ЭНД2", "ЭНД3", "Д"]
    for i, code in enumerate(codes):
        model.add_employee(f"Emp{i}", "permanent")
        model.employees[-1]["days"][0] = code
    errors = check_day(model, 0)
    place_errors = [
        e for e in errors
        if "Место" in e["rule"] and "З" in e["rule"]
    ]
    assert len(place_errors) == 1
    assert "2 сотрудников" in place_errors[0]["message"]


# ---------------------------------------------------------------
# Планы по операционной и эндоскопии
# ---------------------------------------------------------------

def test_too_many_operation_places(model):
    """Заполнено операционных мест больше, чем указано в «О»."""
    model.set_special("О", 0, "1")   # план — 1 операционное место
    codes = ["З", "Б", "Ж", "ЭНД1", "ЭНД2", "ЭНД3", "Д"]   # 3 операции
    for i, code in enumerate(codes):
        model.add_employee(f"Emp{i}", "permanent")
        model.employees[-1]["days"][0] = code
    errors = check_day(model, 0)
    oper_errors = [e for e in errors if e["rule"] == "Операционные"]
    assert len(oper_errors) == 1
    

def test_endo_four_is_invalid(model):
    """Значение 4 для строки «Э» — недопустимо (только 1–3)."""
    model.set_special("Э", 0, "4")
    errors = check_day(model, 0)
    endo_errors = [e for e in errors if e["rule"] == "Места Э"]
    assert len(endo_errors) == 1
    assert "1–3" in endo_errors[0]["message"]


def test_oper_four_is_valid(model):
    """Значение 4 для строки «О» — допустимо (диапазон 1–4)."""
    model.set_special("Э", 0, "3")
    model.set_special("О", 0, "4")
    errors = check_day(model, 0)
    oper_errors = [e for e in errors if e["rule"] == "Места О"]
    assert len(oper_errors) == 0