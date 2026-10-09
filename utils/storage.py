# utils/storage.py

import json
import os
from PyQt5.QtWidgets import QFileDialog, QMessageBox
from models.project_model import ProjectModel
from utils.constants import PROJECT_VERSION, SUPPORTED_VERSIONS
from app_config import ROLE, get


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
        return True
    except PermissionError:
        QMessageBox.critical(None, "Ошибка доступа",
            f"Нет прав на запись в файл:\n{file_path}\n\n"
            "Возможно, файл открыт в другой программе.")
        _cleanup_tmp(tmp_path)
        return False
    except OSError as e:
        QMessageBox.critical(None, "Ошибка файла",
            f"Не удалось записать файл:\n{e}")
        _cleanup_tmp(tmp_path)
        return False
    except Exception as e:
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
        return None, f"Файл не найден:\n{file_path}"
    except PermissionError:
        return None, f"Нет прав на чтение файла:\n{file_path}"
    except UnicodeDecodeError:
        return None, ("Файл не является текстовым JSON.\n"
                      "Возможно, это бинарный файл или повреждён.")
    except OSError as e:
        return None, f"Ошибка чтения файла:\n{e}"

    # 2. Парсинг JSON и валидация — общая с load_model_from_string
    return load_model_from_string(text)


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
    """Общая валидация структуры и сборка ProjectModel.

    Используется и при загрузке из файла, и при загрузке из строки.
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

    # 3. Роль: старые файлы без role считаются врачебными (doctor)
    file_role = data.get("role", "doctor")
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

    # 5. Типы и значения
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

    # 6. Поля «Э» и «О» в special
    for key in ("Э", "О"):
        if key not in special:
            return None, f"В поле 'special' отсутствует ключ «{key}»."
        if not isinstance(special[key], list):
            return None, f"Поле 'special.{key}' должно быть списком."

    # 7. Сотрудники
    for i, emp in enumerate(employees):
        if not isinstance(emp, dict):
            return None, f"Сотрудник #{i + 1} — не объект."
        for field in ("id", "name", "category", "days"):
            if field not in emp:
                return None, f"У сотрудника #{i + 1} отсутствует поле '{field}'."
        if not isinstance(emp["days"], list):
            return None, f"У сотрудника «{emp.get('name', i + 1)}» поле 'days' не список."

    # 8. Сборка модели
    model = ProjectModel()
    try:
        model.from_json(text)
    except Exception as e:
        return None, f"Ошибка разбора данных:\n{e}"

    # 9. Строгая проверка длин массивов
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