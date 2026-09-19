# utils/validation.py

from utils.constants import (
    CODES_OPERATION, CODES_ENDO,
    CATEGORY_PERMANENT, CATEGORY_PARTTIME,
    SPECIAL_VALUES_ENDO, SPECIAL_VALUES_OPER,
)


WORKING_CODES = CODES_OPERATION + CODES_ENDO + ["Д"]

ALLOWED_PERMANENT = [""] + CODES_OPERATION + CODES_ENDO + ["Д", "вых", "до 17", "до 16"]
ALLOWED_PARTTIME = ["", "*"] + CODES_OPERATION + CODES_ENDO + ["Д"]

ALLOWED_SPECIAL_ENDO = list(SPECIAL_VALUES_ENDO)   # Э: 1..3
ALLOWED_SPECIAL_OPER = list(SPECIAL_VALUES_OPER)   # О: 1..4

def _to_int(s):
    try:
        return int(s)
    except (ValueError, TypeError):
        return 0


def check_day(model, day_idx):
    """Проверяет один день (0-based). Возвращает список ошибок."""
    errors = []
    day_num = day_idx + 1
    employees = model.employees
    special = model.special

    e_list = special.get("Э", [])
    o_list = special.get("О", [])
    e_val = e_list[day_idx] if day_idx < len(e_list) else ""
    o_val = o_list[day_idx] if day_idx < len(o_list) else ""

    # Правило 1: заполненность Э и О
    if e_val == "":
        errors.append({"day": day_num, "rule": "Места Э",
                       "message": "Не заполнено число мест в строке «Э»"})
    elif e_val not in ALLOWED_SPECIAL_ENDO:
        errors.append({"day": day_num, "rule": "Места Э",
                       "message": f"Недопустимое значение «{e_val}» в строке «Э» "
                                  f"(допустимо 1–3)"})

    if o_val == "":
        errors.append({"day": day_num, "rule": "Места О",
                       "message": "Не заполнено число мест в строке «О»"})
    elif o_val not in ALLOWED_SPECIAL_OPER:
        errors.append({"day": day_num, "rule": "Места О",
                       "message": f"Недопустимое значение «{o_val}» в строке «О» "
                                  f"(допустимо 1–4)"})
    E = _to_int(e_val)
    O = _to_int(o_val)
    N_planned = E + O + 1

    workplaces = {}
    D_count = 0
    N_actual = 0

    for emp in employees:
        value = emp["days"][day_idx] if day_idx < len(emp["days"]) else ""
        category = emp["category"]

        allowed = ALLOWED_PERMANENT if category == CATEGORY_PERMANENT else ALLOWED_PARTTIME
        if value not in allowed:
            errors.append({"day": day_num, "rule": "Значение",
                           "message": f"Недопустимое значение «{value}» у сотрудника «{emp['name']}»"})
            continue

        if value in WORKING_CODES:
            N_actual += 1
            workplaces.setdefault(value, []).append(emp["name"])
            if value == "Д":
                D_count += 1

    # Правило 2: число работающих
    if N_actual != N_planned:
        errors.append({"day": day_num, "rule": "Работающие",
                       "message": f"Работающих {N_actual}, ожидалось {N_planned}"})

    # Правило 3: ровно один дежурный
    if D_count == 0:
        errors.append({"day": day_num, "rule": "Дежурный",
                       "message": "Отсутствует дежурный"})
    elif D_count > 1:
        errors.append({"day": day_num, "rule": "Дежурный",
                       "message": f"Дежурных {D_count}, должен быть один"})

    # Правило 4: одно место — один сотрудник
    for code, names in workplaces.items():
        if len(names) > 1:
            errors.append({"day": day_num, "rule": f"Место «{code}»",
                           "message": f"На месте «{code}» стоит {len(names)} сотрудников: {', '.join(names)}"})

    # Правило 5: заполненность операционной и эндоскопии
    n_oper = sum(1 for c in CODES_OPERATION if c in workplaces)
    if n_oper > O:
        errors.append({"day": day_num, "rule": "Операционные",
                       "message": f"Занято операционных мест {n_oper}, а по плану {O}"})

    n_endo = sum(1 for c in CODES_ENDO if c in workplaces)
    if n_endo > E:
        errors.append({"day": day_num, "rule": "Эндоскопия",
                       "message": f"Занято эндоскопических мест {n_endo}, а по плану {E}"})

    return errors


def check_schedule(model):
    """Проверяет весь график. Возвращает список ошибок."""
    errors = []
    days = model.days_in_month()
    for day_idx in range(days):
        errors.extend(check_day(model, day_idx))
    return errors