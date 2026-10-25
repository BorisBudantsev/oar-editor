# tests/test_warnings.py

"""Тесты прогностических предупреждений «Мало» и «Избыток работников»."""

import pytest

from models.project_model import ProjectModel
from utils.constants import CATEGORY_PERMANENT, CATEGORY_PARTTIME
from utils.rules import count_day_workforce
from utils.validation import check_day, check_schedule


def _add(model, name, category, value="", day=0):
    """Добавляет сотрудника и ставит значение в указанный день."""
    model.add_employee(name, category)
    model.employees[-1]["days"][day] = value
    return model.employees[-1]


def _warnings(errors):
    """Только прогностические предупреждения."""
    return [
        e for e in errors
        if e["rule"] in ("Мало работников", "Избыток работников")
    ]


def _by_rule(errors, rule):
    return [e for e in errors if e["rule"] == rule]


@pytest.fixture
def plan7():
    """Пустая модель января 2025: Э = О = 3, значит требуется 7."""
    return ProjectModel(month=0, year=2025)


# ---------------------------------------------------------------
# «Мало работников»
# ---------------------------------------------------------------

def test_shortage_warning(plan7):
    """3 доступных постоянных при плане 7 — не хватает 4."""
    for i, code in enumerate(["З", "Б", "Ж"]):
        _add(plan7, f"P{i}", CATEGORY_PERMANENT, code)

    warnings = _by_rule(check_day(plan7, 0), "Мало работников")

    assert len(warnings) == 1
    assert warnings[0]["message"] == (
        "Доступно 3, требуется 7. Не хватает 4."
    )


def test_seven_available_no_warnings(plan7):
    """7 доступных при плане 7 — ни «Мало», ни «Избытка»."""
    for i, code in enumerate(
        ["З", "Б", "Ж", "К", "ЭНД1", "ЭНД2", "ЭНД3"]
    ):
        _add(plan7, f"P{i}", CATEGORY_PERMANENT, code)

    rules = [e["rule"] for e in check_day(plan7, 0)]

    assert "Мало работников" not in rules
    assert "Избыток работников" not in rules


def test_shortage_accounts_for_stars(plan7):
    """4 постоянных + 3 совместителя со «*» = 7 — «Мало» нет."""
    for i, code in enumerate(["З", "Б", "Ж", "К"]):
        _add(plan7, f"P{i}", CATEGORY_PERMANENT, code)
    for i in range(3):
        _add(plan7, f"PT{i}", CATEGORY_PARTTIME, "*")

    rules = [e["rule"] for e in check_day(plan7, 0)]

    assert "Мало работников" not in rules


def test_shortage_accounts_for_parttime_places(plan7):
    """4 постоянных + 3 совместителя на местах = 7 — «Мало» нет."""
    for i, code in enumerate(["З", "Б", "Ж", "К"]):
        _add(plan7, f"P{i}", CATEGORY_PERMANENT, code)
    for i, code in enumerate(["ЭНД1", "ЭНД2", "ЭНД3"]):
        _add(plan7, f"PT{i}", CATEGORY_PARTTIME, code)

    rules = [e["rule"] for e in check_day(plan7, 0)]

    assert "Мало работников" not in rules


def test_shortage_ignores_empty_parttime(plan7):
    """Пустая ячейка совместителя не считается доступностью."""
    for i, code in enumerate(["З", "Б", "Ж", "К"]):
        _add(plan7, f"P{i}", CATEGORY_PERMANENT, code)
    for i in range(3):
        _add(plan7, f"PT{i}", CATEGORY_PARTTIME, "")

    warnings = _by_rule(check_day(plan7, 0), "Мало работников")

    assert len(warnings) == 1
    assert warnings[0]["message"] == (
        "Доступно 4, требуется 7. Не хватает 3."
    )


def test_shortage_ignores_permanent_off(plan7):
    """Постоянные с «вых» не считаются доступными."""
    for i in range(7):
        _add(plan7, f"Off{i}", CATEGORY_PERMANENT, "вых")
    for i, code in enumerate(["З", "Б", "Ж"]):
        _add(plan7, f"P{i}", CATEGORY_PERMANENT, code)

    warnings = _by_rule(check_day(plan7, 0), "Мало работников")

    assert len(warnings) == 1
    assert warnings[0]["message"] == (
        "Доступно 3, требуется 7. Не хватает 4."
    )


def test_reserve_and_duty_are_available(plan7):
    """«до 16», «до 17» и «Д» входят в обе суммы."""
    for i, code in enumerate(["до 16", "до 17", "Д"]):
        _add(plan7, f"P{i}", CATEGORY_PERMANENT, code)

    stats = count_day_workforce(plan7.employees, 0)
    warnings = _by_rule(check_day(plan7, 0), "Мало работников")

    assert stats["available"] == 3
    assert stats["committed"] == 3
    assert len(warnings) == 1
    assert "Доступно 3, требуется 7" in warnings[0]["message"]


# ---------------------------------------------------------------
# «Избыток работников»
# ---------------------------------------------------------------

def test_excess_warning(plan7):
    """10 доступных постоянных при плане 7 — избыток 3.

    Одна ячейка непустая, иначе день считается пустым и правила
    не применяются.
    """
    for i in range(10):
        _add(plan7, f"P{i}", CATEGORY_PERMANENT, "")
    plan7.employees[0]["days"][0] = "З"

    warnings = _by_rule(check_day(plan7, 0), "Избыток работников")

    assert len(warnings) == 1
    assert warnings[0]["message"] == (
        "Доступно 10, требуется 7. Избыток: 3. "
        "Уберите с мест или предоставьте выходной."
    )


def test_excess_ignores_stars(plan7):
    """Совместители со «*» не попадают в Сумму 3."""
    for i, code in enumerate(
        ["З", "Б", "Ж", "К", "ЭНД1", "ЭНД2", "ЭНД3"]
    ):
        _add(plan7, f"P{i}", CATEGORY_PERMANENT, code)
    for i in range(5):
        _add(plan7, f"PT{i}", CATEGORY_PARTTIME, "*")

    rules = [e["rule"] for e in check_day(plan7, 0)]

    assert "Избыток работников" not in rules
    assert "Мало работников" not in rules


def test_excess_counts_parttime_places(plan7):
    """5 постоянных + 5 совместителей на местах — избыток 3."""
    for i in range(5):
        _add(plan7, f"P{i}", CATEGORY_PERMANENT, "")
    for i, code in enumerate(["З", "Б", "Ж", "К", "ЭНД1"]):
        _add(plan7, f"PT{i}", CATEGORY_PARTTIME, code)

    warnings = _by_rule(check_day(plan7, 0), "Избыток работников")

    assert len(warnings) == 1
    assert warnings[0]["message"] == (
        "Доступно 10, требуется 7. Избыток: 3. "
        "Уберите с мест или предоставьте выходной."
    )


# ---------------------------------------------------------------
# Общие сценарии
# ---------------------------------------------------------------

def test_empty_day_has_no_warnings(plan7):
    """Полностью пустой день не даёт прогностических предупреждений."""
    for i in range(3):
        _add(plan7, f"P{i}", CATEGORY_PERMANENT, "")

    assert _warnings(check_day(plan7, 0)) == []


def test_duty_home_ignored(plan7):
    """Флаг duty_home не меняет Суммы 1 и 3."""
    _add(plan7, "P-empty", CATEGORY_PERMANENT, "")
    plan7.employees[-1]["duty_home"][0] = True

    _add(plan7, "P-work", CATEGORY_PERMANENT, "З")
    plan7.employees[-1]["duty_home"][0] = True

    _add(plan7, "PT-star", CATEGORY_PARTTIME, "*")
    plan7.employees[-1]["duty_home"][0] = True

    stats = count_day_workforce(plan7.employees, 0)

    assert stats["available"] == 3
    assert stats["committed"] == 2


def test_shortage_and_excess_never_together():
    """«Мало» и «Избыток» взаимоисключающи: Сумма 1 >= Сумма 3."""
    for count in range(11):
        model = ProjectModel(month=0, year=2025)
        for i in range(count):
            _add(model, f"P{i}", CATEGORY_PERMANENT, "З")

        rules = [e["rule"] for e in check_day(model, 0)]
        assert not (
            "Мало работников" in rules
            and "Избыток работников" in rules
        )


def test_invalid_plan_guard(plan7):
    """Без валидных Э/О прогностические предупреждения не добавляются."""
    plan7.set_special("Э", 0, "")
    plan7.set_special("О", 0, "")
    for i in range(10):
        _add(plan7, f"P{i}", CATEGORY_PERMANENT, "")
    plan7.employees[0]["days"][0] = "З"

    rules = [e["rule"] for e in check_day(plan7, 0)]

    assert "Места Э" in rules
    assert "Места О" in rules
    assert "Мало работников" not in rules
    assert "Избыток работников" not in rules


def test_check_schedule_only_started_days(plan7):
    """Предупреждения появляются только в «начатых» днях."""
    for i in range(10):
        _add(plan7, f"P{i}", CATEGORY_PERMANENT, "")
    # День 1 (индекс 0) начат, остальные дни пусты.
    plan7.employees[0]["days"][0] = "З"

    errors = check_schedule(plan7)
    warning_days = {
        e["day"] for e in errors
        if e["rule"] == "Избыток работников"
    }

    assert warning_days == {1}
