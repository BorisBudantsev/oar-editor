# tests/test_project_model.py

from models.project_model import ProjectModel


# ---------------------------------------------------------------
# days_in_month
# ---------------------------------------------------------------

def test_days_in_month_31():
    model = ProjectModel(month=0, year=2025)
    assert model.days_in_month() == 31


def test_days_in_month_february_regular():
    model = ProjectModel(month=1, year=2025)
    assert model.days_in_month() == 28


def test_days_in_month_february_leap():
    model = ProjectModel(month=1, year=2024)
    assert model.days_in_month() == 29


# ---------------------------------------------------------------
# Сотрудники
# ---------------------------------------------------------------

def test_add_employee_increments_next_id():
    m = ProjectModel(month=0, year=2025)
    id1 = m.add_employee("Иванов", "permanent")
    id2 = m.add_employee("Петров", "parttime")
    assert id1 == 1
    assert id2 == 2
    assert m.next_id == 3
    assert m.get_employee_count() == 2


def test_add_employee_creates_empty_days():
    m = ProjectModel(month=1, year=2025)   # 28 дней
    m.add_employee("Иванов", "permanent")
    emp = m.employees[0]
    assert len(emp["days"]) == 28
    assert all(v == "" for v in emp["days"])


def test_remove_employee():
    m = ProjectModel(month=0, year=2025)
    id1 = m.add_employee("Иванов", "permanent")
    id2 = m.add_employee("Петров", "parttime")
    m.remove_employee(id1)
    assert m.get_employee_count() == 1
    assert m.get_employee(id1) is None
    assert m.get_employee(id2) is not None


# ---------------------------------------------------------------
# Служебные строки
# ---------------------------------------------------------------

def test_special_rows_initialized_with_3():
    m = ProjectModel(month=0, year=2025)   # 31 день
    assert m.special["Э"] == ["3"] * 31
    assert m.special["О"] == ["3"] * 31


# ---------------------------------------------------------------
# set_day / set_special
# ---------------------------------------------------------------

def test_set_day_writes_to_correct_index():
    m = ProjectModel(month=0, year=2025)
    m.add_employee("Иванов", "permanent")
    emp_id = m.employees[0]["id"]
    m.set_day(emp_id, 5, "З")
    assert m.employees[0]["days"][5] == "З"
    assert m.employees[0]["days"][4] == ""
    assert m.employees[0]["days"][6] == ""


def test_set_day_out_of_bounds_ignored():
    m = ProjectModel(month=1, year=2025)   # 28 дней
    m.add_employee("Иванов", "permanent")
    emp_id = m.employees[0]["id"]
    m.set_day(emp_id, 28, "З")             # индекс 28 не существует
    assert all(v == "" for v in m.employees[0]["days"])


# ---------------------------------------------------------------
# JSON round-trip
# ---------------------------------------------------------------

def test_json_roundtrip_preserves_data():
    m = ProjectModel(month=5, year=2026)
    m.add_employee("Иванов", "permanent")
    m.add_employee("Петров", "parttime")
    m.set_day(m.employees[0]["id"], 3, "З")
    m.set_day(m.employees[1]["id"], 7, "*")
    m.set_special("Э", 2, "2")

    json_str = m.to_json()

    restored = ProjectModel()
    restored.from_json(json_str)

    assert restored.month == 5
    assert restored.year == 2026
    assert restored.get_employee_count() == 2
    assert restored.employees[0]["name"] == "Иванов"
    assert restored.employees[0]["days"][3] == "З"
    assert restored.employees[1]["days"][7] == "*"
    assert restored.special["Э"][2] == "2"


# ---------------------------------------------------------------
# Флаг dirty
# ---------------------------------------------------------------

def test_dirty_flag():
    m = ProjectModel(month=0, year=2025)
    assert not m.is_dirty()
    m.add_employee("Иванов", "permanent")
    assert m.is_dirty()
    m.mark_clean()
    assert not m.is_dirty()