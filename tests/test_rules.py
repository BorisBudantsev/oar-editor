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