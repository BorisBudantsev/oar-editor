# tests/test_rules.py

from utils.constants import (
    CATEGORY_PERMANENT, CATEGORY_PARTTIME,
    CODES_PERMANENT, WORKPLACE_CODES,
    SPECIAL_VALUES_ENDO, SPECIAL_VALUES_OPER,
)
from utils.rules import (
    allowed_values,
    normalize_on_clear,
    allowed_special_values,
    is_permanent_available,
    is_parttime_available,
    is_parttime_on_place,
    is_day_started,
    count_day_workforce,
)


# ---------------------------------------------------------------
# allowed_values
# ---------------------------------------------------------------

def test_allowed_values_permanent():
    """Постоянному сотруднику доступны все постоянные коды, без «*»."""
    emp = {"category": CATEGORY_PERMANENT}
    values = set(allowed_values(emp, ""))
    for code in CODES_PERMANENT:
        assert code in values
    assert "*" not in values
    assert "" not in values


def test_allowed_values_parttime_from_empty():
    """Совместитель из пустой ячейки может поставить только «*»."""
    emp = {"category": CATEGORY_PARTTIME}
    assert allowed_values(emp, "") == ["*"]


def test_allowed_values_parttime_from_star():
    """Совместитель из «*» может ставить рабочие коды, но не «*» повторно."""
    emp = {"category": CATEGORY_PARTTIME}
    values = set(allowed_values(emp, "*"))
    for code in WORKPLACE_CODES:
        assert code in values
    assert "*" not in values
    assert "" not in values


def test_allowed_values_parttime_from_working_code():
    """Совместитель с рабочего кода может вернуться к «*» или сменить код."""
    emp = {"category": CATEGORY_PARTTIME}
    values = set(allowed_values(emp, "З"))
    for code in WORKPLACE_CODES:
        assert code in values
    assert "*" in values
    assert "" not in values


# ---------------------------------------------------------------
# normalize_on_clear
# ---------------------------------------------------------------

def test_normalize_on_clear_permanent():
    """Очистка постоянного всегда даёт пустую строку."""
    emp = {"category": CATEGORY_PERMANENT}
    assert normalize_on_clear(emp, "З") == ""
    assert normalize_on_clear(emp, "") == ""


def test_normalize_on_clear_parttime_working():
    """Очистка рабочего кода у совместителя возвращает «*»."""
    emp = {"category": CATEGORY_PARTTIME}
    assert normalize_on_clear(emp, "З") == "*"
    assert normalize_on_clear(emp, "Д") == "*"
    assert normalize_on_clear(emp, "ЭНД1") == "*"


def test_normalize_on_clear_parttime_star():
    """Очистка «*» у совместителя полностью очищает ячейку."""
    emp = {"category": CATEGORY_PARTTIME}
    assert normalize_on_clear(emp, "*") == ""


def test_normalize_on_clear_parttime_empty():
    """Очистка пустой ячейки совместителя ничего не меняет."""
    emp = {"category": CATEGORY_PARTTIME}
    assert normalize_on_clear(emp, "") == ""


# ---------------------------------------------------------------
# allowed_special_values
# ---------------------------------------------------------------

def test_allowed_special_values_endo():
    """В строке «Э» допустимы 1, 2, 3 — но не 4."""
    values = set(allowed_special_values("Э"))
    for v in SPECIAL_VALUES_ENDO:
        assert v in values
    assert "4" not in values


def test_allowed_special_values_oper():
    """В строке «О» допустимы 1, 2, 3, 4."""
    values = set(allowed_special_values("О"))
    for v in SPECIAL_VALUES_OPER:
        assert v in values


# ---------------------------------------------------------------
# Прогностические предупреждения: чистые функции
# ---------------------------------------------------------------

def test_is_permanent_available():
    """Постоянный доступен, если значение не «вых»."""
    for value in ["", "З", "Д", "до 16", "до 17"]:
        assert is_permanent_available(value) is True
    assert is_permanent_available("вых") is False


def test_is_parttime_available():
    """Совместитель доступен со «*» или на конкретном месте."""
    for value in ["*", "З", "Д"]:
        assert is_parttime_available(value) is True
    for value in ["", "вых"]:
        assert is_parttime_available(value) is False


def test_is_parttime_on_place():
    """Совместитель на месте — только рабочий код, не «*»."""
    for value in ["З", "Д"]:
        assert is_parttime_on_place(value) is True
    for value in ["*", ""]:
        assert is_parttime_on_place(value) is False


def test_is_day_started():
    """День начат, если хотя бы у одного сотрудника непустая ячейка."""
    assert is_day_started([], 0) is False
    assert is_day_started([{"days": [""]}], 0) is False
    assert is_day_started([{"days": [""]}, {"days": ["З"]}], 0) is True
    assert is_day_started([{"days": []}], 0) is False


def test_count_day_workforce():
    """Смешанный состав даёт правильные Суммы 1 и 3."""
    employees = [
        {"category": CATEGORY_PERMANENT, "days": [""]},      # обе суммы
        {"category": CATEGORY_PERMANENT, "days": ["вых"]},   # ни одной
        {"category": CATEGORY_PERMANENT, "days": ["З"]},     # обе суммы
        {"category": CATEGORY_PARTTIME, "days": ["*"]},      # только Сумма 1
        {"category": CATEGORY_PARTTIME, "days": ["Д"]},      # обе суммы
        {"category": CATEGORY_PARTTIME, "days": [""]},       # ни одной
    ]
    stats = count_day_workforce(employees, 0)

    assert stats["permanent_available"] == 2
    assert stats["parttime_on_place"] == 1
    assert stats["available"] == 4
    assert stats["committed"] == 3
    assert stats["available"] >= stats["committed"]
