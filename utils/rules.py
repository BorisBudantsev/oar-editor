# utils/rules.py

"""Доменные правила допустимых значений ячеек.

Здесь сосредоточена логика «что можно поставить в ячейку»:

  - для сотрудников — с учётом категории (постоянный/совместитель) и
    правила совместителей (рабочее место ставится только из «*»);
  - для служебных строк «Э» и «О».

Модуль используется:
  - views/delegates.py — построение выпадающего списка;
  - views/main_window.py — проверка значения при вставке из буфера.

Функции возвращают непустые значения; пустая строка получается через
команду «очистить», которая обрабатывается отдельно (normalize_on_clear).
"""

from utils.constants import (
    CATEGORY_PERMANENT,
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