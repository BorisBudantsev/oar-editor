# tests/test_logging_privacy.py

"""Персональные данные (ФИО, содержимое ячеек) не должны попадать в логи.

Сообщение об ошибке может содержать имя сотрудника — оно показывается
пользователю. Но в файл лога ФИО писаться не должно (см. utils/logger.py).
"""

import calendar
import json
import logging

import pytest

from utils.constants import PROJECT_VERSION
from utils.storage import load_model_from_file, load_model_from_string
from models.autosave_model import AutosaveModel


SENSITIVE_NAME = "Секретный Пациент С.С."


@pytest.fixture(autouse=True)
def _clean_autosave():
    AutosaveModel.clear()
    yield
    AutosaveModel.clear()


def _project_json_short_days():
    """Собирает JSON с ошибочной длиной days — валидация назовёт сотрудника."""
    days = calendar.monthrange(2025, 1)[1]
    emp = {
        "id": 1,
        "name": SENSITIVE_NAME,
        "category": "permanent",
        "days": [""] * 5,   # 5 вместо 31
    }
    data = {
        "version": PROJECT_VERSION,
        "role": "doctor",
        "month": 0,
        "year": 2025,
        "employees": [emp],
        "special": {"Э": ["3"] * days, "О": ["3"] * days},
        "notes": [""] * days,
        "nextId": 2,
    }
    return json.dumps(data, ensure_ascii=False)


def _write_bad_project(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(_project_json_short_days(), encoding="utf-8")
    return path


# ---------------------------------------------------------------------
# Загрузка из файла
# ---------------------------------------------------------------------

def test_load_from_file_error_message_contains_name(tmp_path):
    """Пользователь видит ФИО в сообщении — это ожидаемо."""
    path = _write_bad_project(tmp_path)
    model, error = load_model_from_file(str(path))
    assert model is None
    assert SENSITIVE_NAME in error


def test_load_from_file_does_not_log_name(tmp_path, caplog):
    """При этом в логе ФИО отсутствует, но сам факт ошибки залогирован."""
    path = _write_bad_project(tmp_path)
    with caplog.at_level(logging.DEBUG):
        model, error = load_model_from_file(str(path))
    assert model is None
    assert SENSITIVE_NAME not in caplog.text
    assert str(path) in caplog.text


# ---------------------------------------------------------------------
# Загрузка из строки (автосохранение)
# ---------------------------------------------------------------------

def test_load_from_string_does_not_log_name(caplog):
    with caplog.at_level(logging.DEBUG):
        model, error = load_model_from_string(_project_json_short_days())
    assert model is None
    assert SENSITIVE_NAME in error       # сообщение пользователю
    assert SENSITIVE_NAME not in caplog.text


# ---------------------------------------------------------------------
# Автосохранение: содержимое проекта не пишется в лог при сбое
# ---------------------------------------------------------------------

class _InsertFailingCursor:
    def __init__(self, real):
        self._real = real

    def execute(self, sql, parameters=()):
        if sql.strip().upper().startswith("INSERT INTO AUTOSAVE"):
            raise RuntimeError("смоделированный сбой записи")
        return self._real.execute(sql, parameters)

    def __getattr__(self, name):
        return getattr(self._real, name)


class _InsertFailingConnection:
    def __init__(self, real):
        self._real = real

    def cursor(self):
        return _InsertFailingCursor(self._real.cursor())

    def __getattr__(self, name):
        return getattr(self._real, name)


def test_autosave_failure_does_not_log_payload(monkeypatch, caplog):
    import models.autosave_model as autosave_module
    from utils.database import get_connection

    real_get = get_connection
    monkeypatch.setattr(
        autosave_module, "get_connection",
        lambda: _InsertFailingConnection(real_get()),
    )

    payload = json.dumps({"employee": SENSITIVE_NAME}, ensure_ascii=False)
    with caplog.at_level(logging.DEBUG):
        with pytest.raises(RuntimeError):
            AutosaveModel.save(payload)

    assert SENSITIVE_NAME not in caplog.text
