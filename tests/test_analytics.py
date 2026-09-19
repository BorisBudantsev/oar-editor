# tests/test_analytics.py

from models.project_model import ProjectModel
from utils.analytics import (
    _format_ratio, _format_busy,
    compute_employee_stats, compute_totals, build_report,
)


# ---------------------------------------------------------------
# Вспомогательные форматтеры
# ---------------------------------------------------------------

def test_format_ratio_zero_denominator():
    assert _format_ratio(5, 0) == "5/0"


def test_format_ratio_zero_numerator():
    assert _format_ratio(0, 5) == "0/5"


def test_format_ratio_both_zero():
    assert _format_ratio(0, 0) == "0/0"


def test_format_ratio_normal():
    assert _format_ratio(10, 4) == "2.50"


def test_format_busy_both_zero():
    assert _format_busy(0, 0) == "0/0"


def test_format_busy_work_zero():
    assert _format_busy(0, 5) == "0/5"


def test_format_busy_normal():
    assert _format_busy(5, 5) == "0.50"


# ---------------------------------------------------------------
# Статистика по сотрудникам
# ---------------------------------------------------------------

def test_employee_stats_permanent(model):
    model.add_employee("Иванов", "permanent")
    days = model.employees[0]["days"]
    days[0] = "З"
    days[1] = "Б"
    days[2] = "Ж"
    days[3] = "ЭНД1"
    days[4] = "ЭНД2"
    days[5] = "Д"
    days[6] = "вых"
    days[7] = "вых"

    stats = compute_employee_stats(model)
    assert len(stats) == 1
    row = stats[0]
    assert row["name"] == "Иванов"
    assert row["category"] == "permanent"
    assert row["work"] == 6               # 3 операции + 2 ЭНД + 1 Д
    assert row["d_count"] == 1
    assert row["endo"] == 2
    assert row["oper"] == 3
    assert row["vyh"] == 2
    assert row["o_e_ratio"] == "1.50"     # 3/2
    assert row["busy_ratio"] == ""        # для постоянных пусто


def test_employee_stats_parttime(model):
    model.add_employee("Петров", "parttime")
    days = model.employees[0]["days"]
    days[0] = "*"
    days[1] = "*"
    days[2] = "З"
    days[3] = "Ж"

    stats = compute_employee_stats(model)
    row = stats[0]
    assert row["work"] == 2               # только З и Ж
    assert row["vyh"] == ""               # для совместителей пусто
    assert row["busy_ratio"] == "0.50"    # 2 / (2 + 2)


# ---------------------------------------------------------------
# Итоги
# ---------------------------------------------------------------

def test_compute_totals(model):
    model.add_employee("Иванов", "permanent")
    model.add_employee("Петров", "parttime")
    days1 = model.employees[0]["days"]
    days2 = model.employees[1]["days"]
    days1[0] = "З"
    days1[1] = "ЭНД1"
    days1[2] = "Ж"
    days2[0] = "Б"
    days2[1] = "ЭНД2"

    totals = compute_totals(model)
    assert totals["endo"] == 2     # ЭНД1, ЭНД2
    assert totals["oper"] == 3     # З, Ж, Б
    assert totals["zh"] == 1       # один Ж


# ---------------------------------------------------------------
# Структура отчёта
# ---------------------------------------------------------------

def test_build_report_structure(model):
    model.add_employee("Иванов", "permanent")
    report = build_report(model)
    assert "employees" in report
    assert "workplaces" in report
    assert "totals" in report
    assert isinstance(report["employees"], list)
    assert isinstance(report["workplaces"], dict)
    assert isinstance(report["totals"], dict)