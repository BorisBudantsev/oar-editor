# app_config.py

"""Конфигурация приложения, зависящая от роли.

Проект собирается в два исполняемых файла:
- OAR_Doctors.exe — график дежурств врачей
- OAR_Nurses.exe  — график дежурств медицинских сестёр

Роль определяется автоматически по имени exe (см. detect_role()).
При запуске из исходников через `python main.py` роль по умолчанию — doctor.
Можно переопределить аргументом: `python main.py --role nurse`.
"""

import os
import sys


# ----------------------------------------------------------------------
# Константы ролей
# ----------------------------------------------------------------------
ROLE_DOCTOR = "doctor"
ROLE_NURSE = "nurse"


# ----------------------------------------------------------------------
# Определение роли
# ----------------------------------------------------------------------
def detect_role():
    """Возвращает 'doctor' или 'nurse' — в зависимости от имени exe
    или аргумента командной строки.
    """
    # 1. Аргумент командной строки (приоритет)
    if "--role" in sys.argv:
        idx = sys.argv.index("--role")
        if idx + 1 < len(sys.argv):
            value = sys.argv[idx + 1].lower()
            if value in (ROLE_DOCTOR, ROLE_NURSE):
                return value

    # 2. Имя исполняемого файла
    if getattr(sys, "frozen", False):
        exe_name = os.path.basename(sys.executable).lower()
        if "nurse" in exe_name:
            return ROLE_NURSE
        return ROLE_DOCTOR

    # 3. Из исходников — по умолчанию doctor
    return ROLE_DOCTOR


# ----------------------------------------------------------------------
# Параметры, зависящие от роли
# ----------------------------------------------------------------------
ROLE = detect_role()


CONFIG = {
    ROLE_DOCTOR: {
        # Общее
        "role": ROLE_DOCTOR,
        "app_title": "График дежурств врачей",
        "data_folder": "OAR_Doctors",
        "exe_name": "OAR_Doctors",
        "icon": "assets/app_doctors.ico",
        "export_prefix": "График_врачей",

        # Терминология (единственное число / множественное / родительный)
        "person": "врач",
        "person_plural": "врачи",
        "person_genitive": "врачей",       # «Справочник врачей»
        "person_accusative": "врача",      # «Добавить врача»

        # UI
        "directory_title": "Справочник врачей",
        "add_button": "Добавить врача",
        "delete_question": "Удалить врача «{name}» из справочника?",
        "edit_tooltip": "Редактировать врача",
        "add_dialog_title": "Добавить врача",
        "edit_dialog_title": "Редактировать врача",
        "choose_title": "Выберите врачей",
        "choose_subtitle": "Отметьте галочками тех, кто должен попасть в график.",    
        "empty_state": "График дежурств врачей не создан",

        # Экспорт
        "project_filename": "График_врачей_{month}_{year}.json",
        "export_filename": "График_врачей_{month}_{year}.{ext}",
        "export_stats_filename": "Анализ_врачей_{month}_{year}.{ext}",
    },
    ROLE_NURSE: {
        "role": ROLE_NURSE,
        "app_title": "График дежурств медицинских сестёр",
        "data_folder": "OAR_Nurses",
        "exe_name": "OAR_Nurses",
        "icon": "assets/app_nurses.ico",
        "export_prefix": "График_медсестёр",

        "person": "медсестра",
        "person_plural": "медсёстры",
        "person_genitive": "медицинских сестёр",
        "person_accusative": "медсестру",

        "directory_title": "Справочник медицинских сестёр",
        "add_button": "Добавить медсестру",
        "delete_question": "Удалить медсестру «{name}» из справочника?",
        "edit_tooltip": "Редактировать медсестру",
        "add_dialog_title": "Добавить медсестру",
        "edit_dialog_title": "Редактировать медсестру",
        "choose_title": "Выберите медицинских сестёр",
        "choose_subtitle": "Отметьте галочками тех, кто должен попасть в график.",
        "empty_state": "График дежурств медицинских сестёр не создан",

        "project_filename": "График_медсестёр_{month}_{year}.json",
        "export_filename": "График_медсестёр_{month}_{year}.{ext}",
        "export_stats_filename": "Анализ_медсестёр_{month}_{year}.{ext}",
    },
}


def get(key):
    """Возвращает значение параметра для текущей роли.

    Пример:
        from app_config import get
        title = get("app_title")
    """
    return CONFIG[ROLE][key]


def is_doctor():
    return ROLE == ROLE_DOCTOR


def is_nurse():
    return ROLE == ROLE_NURSE