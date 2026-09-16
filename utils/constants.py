# utils/constants.py

CATEGORY_PERMANENT = "permanent"
CATEGORY_PARTTIME = "parttime"
CATEGORIES = [CATEGORY_PERMANENT, CATEGORY_PARTTIME]

CODES_OPERATION = ["З", "Б", "Ж", "К"]
CODES_ENDO = ["ЭНД1", "ЭНД2", "ЭНД3"]

# Коды рабочих мест (З, Б, Ж, К, ЭНД1-3, Д)
WORKPLACE_CODES = CODES_OPERATION + CODES_ENDO + ["Д"]

# Наборы для делегата (без "очистить" — оно добавится в делегате)
CODES_PERMANENT = CODES_OPERATION + CODES_ENDO + ["Д", "вых", "до 17", "до 16"]
CODES_PARTTIME = ["*"] + WORKPLACE_CODES

SPECIAL_ROWS = ["Э", "О"]
SPECIAL_VALUES = ["1", "2", "3", "4"]

# Метка пункта "Очистить" в выпадающем меню
CLEAR_LABEL = "очистить"

MONTHS = [
    "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
]

PROJECT_VERSION = "1.0"