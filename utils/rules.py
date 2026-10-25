# utils/rules.py

"""Доменные правила допустимых значений ячеек.

Здесь сосредоточена логика «что можно поставить в ячейку»:

  - для сотрудников — с учётом категории (постоянный/совместитель) и
    правила совместителей (рабочее место ставится только из «*»);
  - для служебных строк «Э» и «О».

Модуль используется:
  - views/delegates.py — построение выпадающего списка;
  - views/main_window.py — проверка значения при вставке из буфера;
  - utils/validation.py — прогностические предупреждения по дню.

Функции возвращают непустые значения; пустая строка получается через
команду «очистить», которая обрабатывается отдельно (normalize_on_clear).
"""

from utils.constants import (
    CATEGORY_PERMANENT,
    CATEGORY_PARTTIME,
    CODES_PERMANENT,
    WORKPLACE_CODES,
    SPECIAL_VALUES_ENDO,
    SPECIAL_VALUES_OPER,
)


def allowed_values(employee, current_value):
    """Допустимые непустые значения для ячейки сотрудника.

    Параметры:
      employee — словарь сотрудника (нужен ключ 'category').
      current_value — текущее значение в ячейке (для совместителей
        оно определяет, какие переходы разрешены).

    Правила:
      - постоянный: любые коды CODES_PERMANENT;
      - совместитель:
          "" → только «*» (сначала отмечает доступность),
          "*" → рабочие коды,
          рабочий код → рабочие коды + «*» (откат к доступности).
    """
    if employee.get("category") == CATEGORY_PERMANENT:
        return list(CODES_PERMANENT)

    # Совместитель
    if current_value == "":
        return ["*"]
    if current_value == "*":
        return list(WORKPLACE_CODES)
    # current_value — рабочий код
    return list(WORKPLACE_CODES) + ["*"]


def normalize_on_clear(employee, current_value):
    """Значение, которое надо подставить при команде «очистить».

    Для постоянного — всегда пустая строка.
    Для совместителя:
      - если стоит рабочий код — возвращаем «*» (сотрудник снова доступен);
      - если стоит «*» или пусто — возвращаем пустую строку.
    """
    if employee.get("category") == CATEGORY_PERMANENT:
        return ""

    if current_value in WORKPLACE_CODES:
        return "*"
    return ""


def is_permanent_available(value):
    """Постоянный работник не в явном выходном.

    Пустая ячейка, резерв («до 16», «до 17»), рабочее место и «Д»
    считаются потенциально доступными. Флаг duty_home не учитывается.
    """
    return value != "вых"


def is_parttime_available(value):
    """Совместитель доступен: отметил «*» или уже стоит на месте."""
    return value == "*" or value in WORKPLACE_CODES


def is_parttime_on_place(value):
    """Совместитель стоит на конкретном рабочем месте, а не на «*»."""
    return value in WORKPLACE_CODES


def is_day_started(employees, day_idx):
    """День «начат», если хотя бы у одного сотрудника ячейка не пустая."""
    for emp in employees:
        days = emp.get("days", [])
        if 0 <= day_idx < len(days) and days[day_idx] != "":
            return True
    return False


def count_day_workforce(employees, day_idx):
    """Считает Суммы 1 и 3 для дня (0-based).

    Возвращает:
      available  — Сумма 1: постоянные не в «вых» + совместители «*»/на месте;
      committed  — Сумма 3: постоянные не в «вых» + совместители на месте;
      permanent_available, parttime_on_place — для отладки/тестов.

    duty_home намеренно не используется: учитывается только days[day_idx].
    """
    permanent_available = 0
    parttime_available = 0
    parttime_on_place = 0

    for emp in employees:
        days = emp.get("days", [])
        value = days[day_idx] if 0 <= day_idx < len(days) else ""
        category = emp.get("category")

        if category == CATEGORY_PERMANENT:
            if is_permanent_available(value):
                permanent_available += 1
        elif category == CATEGORY_PARTTIME:
            if is_parttime_available(value):
                parttime_available += 1
            if is_parttime_on_place(value):
                parttime_on_place += 1

    return {
        "available": permanent_available + parttime_available,
        "committed": permanent_available + parttime_on_place,
        "permanent_available": permanent_available,
        "parttime_on_place": parttime_on_place,
    }


def allowed_special_values(row_key):
    """Допустимые значения для служебных строк «Э» и «О».

    «Э» — 1–3 (ЭНД1..ЭНД3).
    «О» — 1–4 (З, Б, Ж, К).

    Пустая строка — это «не заполнено». Валидация её не одобрит,
    но команда «очистить» — отдельный сценарий, здесь она не нужна.
    """
    if row_key == "Э":
        return list(SPECIAL_VALUES_ENDO)
    return list(SPECIAL_VALUES_OPER)