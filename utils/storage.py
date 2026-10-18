# utils/storage.py

import json
import logging
import os
from PyQt5.QtWidgets import QFileDialog, QMessageBox
from models.project_model import ProjectModel
from utils.constants import (
    PROJECT_VERSION, SUPPORTED_VERSIONS, CATEGORIES, CATEGORY_PERMANENT,
)
from utils.validation import (
    ALLOWED_PERMANENT, ALLOWED_PARTTIME,
    ALLOWED_SPECIAL_ENDO, ALLOWED_SPECIAL_OPER,
)
from app_config import ROLE, get


logger = logging.getLogger(__name__)

# Роли, допустимые в JSON-проекте.
VALID_ROLES = ("doctor", "nurse")


def _is_int(value):
    """True для целого числа, но не для bool.

    В Python ``bool`` — подкласс ``int``, поэтому ``isinstance(True, int)``
    истинно. Для полей month/year/nextId/id логическое значение недопустимо.
    """
    return isinstance(value, int) and not isinstance(value, bool)


# ----------------------------------------------------------------------
# Сохранение
# ----------------------------------------------------------------------
def _cleanup_tmp(tmp_path):
    """Удаляет временный файл, если он остался после ошибки."""
    try:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
    except OSError:
        pass


def save_model_to_file(model, file_path):
    """Сохраняет модель в JSON-файл атомарно. Возвращает True при успехе.

    Запись идёт во временный файл рядом с целевым, затем os.replace
    атомарно подменяет целевой файл. Если что-то пойдёт не так на любом
    этапе (включая отключение питания), старый файл останется целым.
    """
    # 1. Сериализация — если тут ошибка, целевой файл вообще не трогаем
    try:
        data = model.to_json()
    except Exception as e:
        logger.exception("Ошибка подготовки данных для сохранения: %s", e)
        QMessageBox.critical(None, "Ошибка сохранения",
            f"Не удалось подготовить данные для сохранения:\n{e}")
        return False

    tmp_path = file_path + ".tmp"
    try:
        # 2. Пишем во временный файл рядом с целевым
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        # 3. Атомарная подмена. На NTFS и большинстве ФС это одна операция.
        os.replace(tmp_path, file_path)
        logger.info("Проект сохранён: %s", file_path)
        return True
    except PermissionError as e:
        logger.exception("Нет прав на запись: %s", file_path)
        QMessageBox.critical(None, "Ошибка доступа",
            f"Нет прав на запись в файл:\n{file_path}\n\n"
            "Возможно, файл открыт в другой программе.")
        _cleanup_tmp(tmp_path)
        return False
    except OSError as e:
        logger.exception("Ошибка записи файла: %s", file_path)
        QMessageBox.critical(None, "Ошибка файла",
            f"Не удалось записать файл:\n{e}")
        _cleanup_tmp(tmp_path)
        return False
    except Exception as e:
        logger.exception("Ошибка сохранения проекта: %s", file_path)
        QMessageBox.critical(None, "Ошибка сохранения",
            f"Не удалось сохранить файл:\n{e}")
        _cleanup_tmp(tmp_path)
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
        logger.error("Файл не найден: %s", file_path)
        return None, f"Файл не найден:\n{file_path}"
    except PermissionError:
        logger.error("Нет прав на чтение: %s", file_path)
        return None, f"Нет прав на чтение файла:\n{file_path}"
    except UnicodeDecodeError:
        logger.error("Файл не является текстовым JSON: %s", file_path)
        return None, ("Файл не является текстовым JSON.\n"
                      "Возможно, это бинарный файл или повреждён.")
    except OSError as e:
        logger.exception("Ошибка чтения файла: %s", file_path)
        return None, f"Ошибка чтения файла:\n{e}"

    # 2. Парсинг JSON и валидация — общая с load_model_from_string
    model, error = load_model_from_string(text)
    if model is None:
        # В error может быть ФИО сотрудника — в лог его не пишем.
        logger.error("Загрузка проекта не удалась: %s", file_path)
        return None, error

    logger.info(
        "Проект загружен: %s (месяц=%d, год=%d, сотрудников=%d)",
        file_path, model.month, model.year, model.get_employee_count(),
    )
    return model, ""


def load_model_from_string(text):
    """Загружает модель из строки JSON (та же валидация, что и для файла).

    Возвращает (model, message)."""
    # 1. Парсинг JSON
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        return None, (f"Файл повреждён или не является JSON:\n{e}\n\n"
                      f"Строка {e.lineno}, позиция {e.colno}.")

    # 2. Общая валидация структуры и сборка модели
    return _validate_and_build(text, data)


def _validate_and_build(text, data):
    """Строгая валидация структуры и содержимого JSON и сборка ProjectModel.

    Используется и при загрузке из файла, и при загрузке из строки.
    Молчаливое «исправление» повреждённых современных файлов недопустимо —
    при несоответствии файл отклоняется целиком. Для отсутствующих полей
    старых форматов (role, notes, duty_home) применяются только
    предусмотренные миграционные значения (см. ProjectModel.from_json).
    """
    # 1. Корневой элемент — объект
    if not isinstance(data, dict):
        return None, "Неверная структура: корневой элемент должен быть объектом."

    # 2. Версия
    version = data.get("version")
    if version is None:
        return None, "В файле отсутствует поле 'version'."
    if version not in SUPPORTED_VERSIONS:
        supported = ", ".join(SUPPORTED_VERSIONS)
        return None, (
            f"Несовместимая версия файла.\n\n"
            f"Файл: {version}\n"
            f"Поддерживаемые версии: {supported}\n"
            f"Актуальная: {PROJECT_VERSION}"
        )

    # 3. Роль: старые файлы (1.0) без поля считаются врачебными (doctor)
    if "role" in data:
        file_role = data["role"]
        if not isinstance(file_role, str) or file_role not in VALID_ROLES:
            return None, (
                f"Некорректное значение поля 'role': {file_role!r}. "
                f"Ожидается 'doctor' или 'nurse'."
            )
    else:
        file_role = "doctor"
    if file_role != ROLE:
        file_role_name = "врачей" if file_role == "doctor" else "медицинских сестёр"
        current_role_name = "врачей" if ROLE == "doctor" else "медицинских сестёр"
        return None, (
            f"Этот файл создан для графика дежурств {file_role_name}.\n\n"
            f"Текущее приложение работает с графиком {current_role_name}.\n"
            f"Откройте файл в соответствующем приложении."
        )

    # 4. Обязательные поля
    required = ["month", "year", "employees", "special", "nextId"]
    missing = [k for k in required if k not in data]
    if missing:
        return None, f"В файле отсутствуют обязательные поля: {', '.join(missing)}"

    # 5. Типы и значения верхнего уровня
    month = data["month"]
    year = data["year"]
    employees = data["employees"]
    special = data["special"]
    next_id = data["nextId"]

    if not _is_int(month) or not (0 <= month <= 11):
        return None, f"Некорректный месяц: {month!r}. Ожидается целое 0–11."
    if not _is_int(year) or not (1900 <= year <= 2200):
        return None, f"Некорректный год: {year!r}. Ожидается целое 1900–2200."
    if not isinstance(employees, list):
        return None, "Поле 'employees' должно быть списком."
    if not isinstance(special, dict):
        return None, "Поле 'special' должно быть объектом."
    if not _is_int(next_id) or next_id < 1:
        return None, f"Некорректное значение nextId: {next_id!r}. Ожидается целое ≥ 1."

    # 6. Поля «Э» и «О» в special: ключи, тип и допустимые значения
    special_allowed = {"Э": ALLOWED_SPECIAL_ENDO, "О": ALLOWED_SPECIAL_OPER}
    for key in ("Э", "О"):
        if key not in special:
            return None, f"В поле 'special' отсутствует ключ «{key}»."
        if not isinstance(special[key], list):
            return None, f"Поле 'special.{key}' должно быть списком."
    # Любые дополнительные ключи special тоже должны быть списками
    for key, values in special.items():
        if not isinstance(values, list):
            return None, f"Поле 'special.{key}' должно быть списком."
    for key, allowed in special_allowed.items():
        for pos, value in enumerate(special[key]):
            if not isinstance(value, str):
                return None, (
                    f"Недопустимый тип в строке «{key}» (день {pos + 1}): "
                    f"ожидается строка."
                )
            if value != "" and value not in allowed:
                return None, (
                    f"Недопустимое значение «{value}» в служебной строке «{key}» "
                    f"(день {pos + 1})."
                )

    # 7. Сотрудники
    seen_ids = set()
    max_id = 0
    for i, emp in enumerate(employees):
        if not isinstance(emp, dict):
            return None, f"Сотрудник #{i + 1} — не объект."
        for field in ("id", "name", "category", "days"):
            if field not in emp:
                return None, f"У сотрудника #{i + 1} отсутствует поле '{field}'."

        emp_id = emp["id"]
        if not _is_int(emp_id) or emp_id < 1:
            return None, (
                f"У сотрудника #{i + 1} некорректный id: {emp_id!r}. "
                f"Ожидается целое ≥ 1."
            )
        if emp_id in seen_ids:
            return None, f"Повторяющийся id сотрудника: {emp_id}."
        seen_ids.add(emp_id)
        max_id = max(max_id, emp_id)

        if not isinstance(emp["name"], str):
            return None, f"У сотрудника #{i + 1} поле 'name' должно быть строкой."

        category = emp["category"]
        if category not in CATEGORIES:
            return None, (
                f"У сотрудника «{emp['name']}» недопустимая категория: "
                f"{category!r}. Ожидается permanent или parttime."
            )

        days = emp["days"]
        if not isinstance(days, list):
            return None, f"У сотрудника «{emp['name']}» поле 'days' не список."

        allowed_values = (ALLOWED_PERMANENT if category == CATEGORY_PERMANENT
                          else ALLOWED_PARTTIME)
        for pos, value in enumerate(days):
            if not isinstance(value, str):
                return None, (
                    f"У сотрудника «{emp['name']}» в дне {pos + 1} "
                    f"значение не является строкой."
                )
            if value not in allowed_values:
                return None, (
                    f"У сотрудника «{emp['name']}» недопустимое значение "
                    f"«{value}» в дне {pos + 1}."
                )

        # duty_home — строго массив bool (если присутствует)
        if "duty_home" in emp:
            duty_home = emp["duty_home"]
            if not isinstance(duty_home, list):
                return None, (
                    f"У сотрудника «{emp['name']}» поле 'duty_home' "
                    f"должно быть списком."
                )
            for pos, flag in enumerate(duty_home):
                if not isinstance(flag, bool):
                    return None, (
                        f"У сотрудника «{emp['name']}» в поле 'duty_home' "
                        f"день {pos + 1} не является логическим значением."
                    )

    # 8. Примечания (если присутствуют)
    if "notes" in data:
        notes = data["notes"]
        if not isinstance(notes, list):
            return None, "Поле 'notes' должно быть списком."
        for pos, value in enumerate(notes):
            if not isinstance(value, str):
                return None, (
                    f"Элемент {pos + 1} поля 'notes' должен быть строкой."
                )

    # 9. Согласованность nextId с идентификаторами сотрудников:
    #    nextId — следующий свободный id, он должен быть больше любого id.
    if next_id <= max_id:
        return None, (
            f"Поле 'nextId' ({next_id}) не согласовано с id сотрудников "
            f"(максимальный id = {max_id})."
        )

    # 10. Сборка модели
    model = ProjectModel()
    try:
        model.from_json(text)
    except Exception as e:
        return None, f"Ошибка разбора данных:\n{e}"

    # 11. Строгая проверка длин массивов
    target_days = model.days_in_month()
    try:
        _validate_days_lengths(model, target_days)
    except ValueError as e:
        return None, f"Повреждённый файл: {e}"

    return model, ""


def _validate_days_lengths(model, target_days):
    """Проверяет, что длины массивов days / special / notes / duty_home
    равны target_days.

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
            raise ValueError(f"Служебная строка «{key}» — не список.")
        if len(values) != target_days:
            raise ValueError(
                f"В служебной строке «{key}» длина = {len(values)}, "
                f"ожидается {target_days}."
            )

    if not isinstance(model.notes, list):
        raise ValueError("Поле 'notes' — не список.")
    if len(model.notes) != target_days:
        raise ValueError(
            f"В поле 'notes' длина = {len(model.notes)}, "
            f"ожидается {target_days}."
        )

    for emp in model.employees:
        dh = emp.get("duty_home", [])
        if not isinstance(dh, list):
            raise ValueError(
                f"У сотрудника «{emp.get('name', '?')}» "
                f"поле duty_home — не список."
            )
        if len(dh) != target_days:
            raise ValueError(
                f"У сотрудника «{emp.get('name', '?')}» "
                f"длина duty_home = {len(dh)}, ожидается {target_days}."
            )


# ----------------------------------------------------------------------
# Диалоги
# ----------------------------------------------------------------------
def ask_save_path(parent, default_name="project.json"):
    path, _ = QFileDialog.getSaveFileName(
        parent, "Сохранить проект", default_name,
        "График ОАР (*.json);;Все файлы (*)"
    )
    return path if path else None


def ask_open_path(parent):
    path, _ = QFileDialog.getOpenFileName(
        parent, "Открыть проект", "",
        "График ОАР (*.json);;Все файлы (*)"
    )
    return path if path else None