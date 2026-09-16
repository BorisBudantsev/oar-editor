# utils/analytics.py

from utils.constants import (
    CATEGORY_PERMANENT, CATEGORY_PARTTIME,
    CODES_OPERATION, CODES_ENDO
)

ENDOSCOPY_CODES = list(CODES_ENDO)          # ЭНД1, ЭНД2, ЭНД3
OPERATION_CODES = list(CODES_OPERATION)     # З, Б, Ж, К
WORKING_CODES = OPERATION_CODES + ENDOSCOPY_CODES + ["Д"]


def _count(values, codes):
    return sum(1 for v in values if v in codes)


def _format_ratio(a, b):
    """Отношение a/b.

    Оба > 0   → '1.50' (2 знака после запятой)
    b == 0    → 'N/0'
    a == 0    → '0/N'
    """
    if b == 0:
        return f"{a}/0"
    if a == 0:
        return f"0/{b}"
    return f"{a / b:.2f}"


def _format_busy(work, stars):
    """Коэффициент занятости: work / (work + stars).

    Знаменатель 0     → '0/0'
    Числитель 0       → '0/N'
    Иначе             → десятичная дробь с 2 знаками
    """
    denom = work + stars
    if denom == 0:
        return "0/0"
    if work == 0:
        return f"0/{stars}"
    return f"{work / denom:.2f}"


# ----------------------------------------------------------------------
# Отчёт по сотрудникам
# ----------------------------------------------------------------------
def compute_employee_stats(model):
    days = model.days_in_month()
    rows = []

    for emp in model.employees:
        values = emp["days"][:days]
        work = _count(values, WORKING_CODES)
        endo = _count(values, ENDOSCOPY_CODES)
        oper = _count(values, OPERATION_CODES)
        d_count = _count(values, ["Д"])
        vyh = _count(values, ["вых"])
        stars = _count(values, ["*"])

        is_perm = emp["category"] == CATEGORY_PERMANENT

        rows.append({
            "name": emp["name"],
            "category": emp["category"],
            "work": work,
            "vyh": vyh if is_perm else "",
            "d_count": d_count,
            "endo": endo,
            "oper": oper,
            "o_e_ratio": _format_ratio(oper, endo),
            "busy_ratio": "" if is_perm else _format_busy(work, stars),
        })

    return rows


# ----------------------------------------------------------------------
# Отчёт по рабочим местам (с ранжированием)
# ----------------------------------------------------------------------
def compute_workplace_stats(model):
    days = model.days_in_month()

    endo_rows = []
    oper_rows = []
    d_rows = []
    ratio_rows = []     # [ФИО, строка, ключ сортировки]
    busy_rows = []      # [ФИО, строка, ключ сортировки]

    for emp in model.employees:
        values = emp["days"][:days]
        endo = _count(values, ENDOSCOPY_CODES)
        oper = _count(values, OPERATION_CODES)
        d_count = _count(values, ["Д"])
        stars = _count(values, ["*"])
        work = _count(values, WORKING_CODES)

        endo_rows.append([emp["name"], endo])
        oper_rows.append([emp["name"], oper])
        d_rows.append([emp["name"], d_count])

        # ключ сортировки для О/Э
        if endo == 0:
            ratio_sort = float("inf") if oper > 0 else 0.0
        else:
            ratio_sort = oper / endo
        ratio_rows.append([emp["name"], _format_ratio(oper, endo), ratio_sort])

        if emp["category"] == CATEGORY_PARTTIME:
            denom = work + stars
            busy_sort = 0.0 if denom == 0 else work / denom
            busy_rows.append([emp["name"], _format_busy(work, stars), busy_sort])

    endo_rows.sort(key=lambda x: -x[1])
    oper_rows.sort(key=lambda x: -x[1])
    d_rows.sort(key=lambda x: -x[1])
    ratio_rows.sort(key=lambda x: -x[2])
    busy_rows.sort(key=lambda x: -x[2])

    return {
        "endo": endo_rows,
        "oper": oper_rows,
        "d": d_rows,
        "ratio": [[n, r] for n, r, _ in ratio_rows],
        "busy": [[n, r] for n, r, _ in busy_rows],
    }


# ----------------------------------------------------------------------
# Общий итог
# ----------------------------------------------------------------------
def compute_totals(model):
    days = model.days_in_month()
    total_endo = 0
    total_oper = 0
    total_zh = 0

    for emp in model.employees:
        values = emp["days"][:days]
        total_endo += _count(values, ENDOSCOPY_CODES)
        total_oper += _count(values, OPERATION_CODES)
        total_zh += _count(values, ["Ж"])

    return {
        "endo": total_endo,
        "oper": total_oper,
        "zh": total_zh,
    }


def build_report(model):
    return {
        "employees": compute_employee_stats(model),
        "workplaces": compute_workplace_stats(model),
        "totals": compute_totals(model),
    }