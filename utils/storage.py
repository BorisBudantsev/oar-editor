# utils/storage.py

import json
from PyQt5.QtWidgets import QFileDialog, QMessageBox
from models.project_model import ProjectModel
from utils.constants import PROJECT_VERSION


# ----------------------------------------------------------------------
# Сохранение
# ----------------------------------------------------------------------
def save_model_to_file(model, file_path):
    """Сохраняет модель в JSON-файл. Возвращает True при успехе."""
    try:
        data = model.to_json()
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(data)
        return True
    except PermissionError:
        QMessageBox.critical(None, "Ошибка доступа",
            f"Нет прав на запись в файл:\n{file_path}\n\n"
            "Возможно, файл открыт в другой программе.")
        return False
    except OSError as e:
        QMessageBox.critical(None, "Ошибка файла",
            f"Не удалось записать файл:\n{e}")
        return False
    except Exception as e:
        QMessageBox.critical(None, "Ошибка сохранения",
            f"Не удалось сохранить файл:\n{e}")
        return False


# ----------------------------------------------------------------------
# Загрузка
# ----------------------------------------------------------------------
def load_model_from_file(file_path):
    """Загружает модель из JSON-файла.

    Возвращает (model, message):
      - (ProjectModel, "")    — успех
      - (None, "текст ошибки") — неудача
    """
    # 1. Чтение файла
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        return None, f"Файл не найден:\n{file_path}"
    except PermissionError:
        return None, f"Нет прав на чтение файла:\n{file_path}"
    except UnicodeDecodeError:
        return None, ("Файл не является текстовым JSON.\n"
                      "Возможно, это бинарный файл или повреждён.")
    except OSError as e:
        return None, f"Ошибка чтения файла:\n{e}"

    # 2. Парсинг JSON
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        return None, (f"Файл повреждён или не является JSON:\n{e}\n\n"
                      f"Строка {e.lineno}, позиция {e.colno}.")

    if not isinstance(data, dict):
        return None, "Неверная структура: корневой элемент должен быть объектом."

    # 3. Проверка версии
    version = data.get("version")
    if version is None:
        return None, "В файле отсутствует поле 'version'."
    if version != PROJECT_VERSION:
        return None, (f"Несовместимая версия файла.\n\n"
                      f"Файл: {version}\nПрограмма ожидает: {PROJECT_VERSION}")

    # 4. Обязательные поля
    required = ["month", "year", "employees", "special", "nextId"]
    missing = [k for k in required if k not in data]
    if missing:
        return None, f"В файле отсутствуют обязательные поля: {', '.join(missing)}"

    # 5. Проверка типов и значений
    month = data["month"]
    year = data["year"]
    employees = data["employees"]
    special = data["special"]
    next_id = data["nextId"]

    if not isinstance(month, int) or not (0 <= month <= 11):
        return None, f"Некорректный месяц: {month}. Ожидается 0–11."
    if not isinstance(year, int) or not (1900 <= year <= 2200):
        return None, f"Некорректный год: {year}. Ожидается 1900–2200."
    if not isinstance(employees, list):
        return None, "Поле 'employees' должно быть списком."
    if not isinstance(special, dict):
        return None, "Поле 'special' должно быть объектом."
    if not isinstance(next_id, int) or next_id < 1:
        return None, f"Некорректное значение nextId: {next_id}."

    # 6. Проверка special
    for key in ("Э", "О"):
        if key not in special:
            return None, f"В поле 'special' отсутствует ключ «{key}»."
        if not isinstance(special[key], list):
            return None, f"Поле 'special.{key}' должно быть списком."

    # 7. Проверка сотрудников
    for i, emp in enumerate(employees):
        if not isinstance(emp, dict):
            return None, f"Сотрудник #{i + 1} — не объект."
        for field in ("id", "name", "category", "days"):
            if field not in emp:
                return None, f"У сотрудника #{i + 1} отсутствует поле '{field}'."
        if not isinstance(emp["days"], list):
            return None, f"У сотрудника «{emp.get('name', i + 1)}» поле 'days' не список."

    # 8. Создаём модель через обычный from_json (структура проверена)
    model = ProjectModel()
    try:
        model.from_json(text)
    except Exception as e:
        return None, f"Ошибка разбора данных:\n{e}"

    # 9. Проверяем длину массивов (без молчаливого исправления)
    target_days = model.days_in_month()
    try:
        _validate_days_lengths(model, target_days)
    except ValueError as e:
        return None, f"Повреждённый файл: {e}"

    return model, ""


def _validate_days_lengths(model, target_days):
    """Проверяет, что длины массивов days и special равны target_days.

    При несоответствии возбуждает ValueError — молчаливое исправление
    повреждённых данных недопустимо для медицинского графика.
    """
    for emp in model.employees:
        days = emp.get("days", [])
        if len(days) != target_days:
            raise ValueError(
                f"У сотрудника «{emp.get('name', '?')}» "
                f"длина массива days = {len(days)}, ожидается {target_days}."
            )

    for key, values in model.special.items():
        if not isinstance(values, list):
            raise ValueError(
                f"Служебная строка «{key}» — не список."
            )
        if len(values) != target_days:
            raise ValueError(
                f"В служебной строке «{key}» длина = {len(values)}, "
                f"ожидается {target_days}."
            )

# ----------------------------------------------------------------------
# Диалоги
# ----------------------------------------------------------------------
def ask_save_path(parent, default_name="project.json"):
    path, _ = QFileDialog.getSaveFileName(
        parent, "Сохранить проект", default_name, "График ОАР (*.json);;Все файлы (*)"
    )
    return path if path else None


def ask_open_path(parent):
    path, _ = QFileDialog.getOpenFileName(
        parent, "Открыть проект", "", "График ОАР (*.json);;Все файлы (*)"
    )
    return path if path else None
def load_model_from_string(text):
    """Загружает модель из строки JSON (та же валидация, что и для файла).

    Возвращает (model, message)."""
    import json
    # Обёртка: пишем текст во временную переменную и переиспользуем логику
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        return None, f"JSON повреждён: {e}"

    # Полная валидация — та же, что при загрузке из файла.
    # Для повторного использования обернём текст в BytesIO и вызовем
    # внутреннюю проверку.
    return _validate_and_build(text, data)


def _validate_and_build(text, data):
    """Внутренняя: применяет те же проверки, что load_model_from_file."""
    if not isinstance(data, dict):
        return None, "Неверная структура: корень должен быть объектом."

    version = data.get("version")
    if version is None:
        return None, "Отсутствует поле 'version'."
    if version != PROJECT_VERSION:
        return None, (f"Несовместимая версия: {version}. "
                      f"Ожидается {PROJECT_VERSION}.")

    required = ["month", "year", "employees", "special", "nextId"]
    missing = [k for k in required if k not in data]
    if missing:
        return None, f"Отсутствуют поля: {', '.join(missing)}"

    month = data["month"]
    year = data["year"]
    if not isinstance(month, int) or not (0 <= month <= 11):
        return None, f"Некорректный месяц: {month}"
    if not isinstance(year, int) or not (1900 <= year <= 2200):
        return None, f"Некорректный год: {year}"
    if not isinstance(data["employees"], list):
        return None, "employees не список"
    if not isinstance(data["special"], dict):
        return None, "special не объект"
    if not isinstance(data["nextId"], int) or data["nextId"] < 1:
        return None, "Некорректный nextId"

    for key in ("Э", "О"):
        if key not in data["special"]:
            return None, f"special не содержит «{key}»"
        if not isinstance(data["special"][key], list):
            return None, f"special.{key} не список"

    for i, emp in enumerate(data["employees"]):
        if not isinstance(emp, dict):
            return None, f"Сотрудник #{i + 1} не объект"
        for f in ("id", "name", "category", "days"):
            if f not in emp:
                return None, f"У сотрудника #{i + 1} нет поля '{f}'"
        if not isinstance(emp["days"], list):
            return None, f"У сотрудника «{emp.get('name', i + 1)}» days не список"

    from models.project_model import ProjectModel
    model = ProjectModel()
    try:
        model.from_json(text)
    except Exception as e:
        return None, f"Ошибка разбора: {e}"

    target = model.days_in_month()
    try:
        _validate_days_lengths(model, target)
    except ValueError as e:
        return None, f"Повреждённый файл: {e}"
    return model, ""