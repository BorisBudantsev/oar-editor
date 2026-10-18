# tests/test_autosave_model.py

"""Модель автосохранения: в базе всегда остаётся ровно одна актуальная копия.

Порядок операций (сначала INSERT новой записи, затем DELETE старых)
гарантирует, что при сбое записи новой версии предыдущая пригодная
копия несохранённых данных не теряется.
"""

import contextlib

import pytest

from models.autosave_model import AutosaveModel
from utils.database import get_connection


@pytest.fixture(autouse=True)
def _clean():
    AutosaveModel.clear()
    yield
    AutosaveModel.clear()


def _count_rows():
    with contextlib.closing(get_connection()) as conn:
        return conn.execute("SELECT COUNT(*) FROM autosave").fetchone()[0]


# ---------------------------------------------------------------------
# Обычное поведение
# ---------------------------------------------------------------------

def test_save_then_load_returns_payload():
    AutosaveModel.save('{"a": 1}')
    assert AutosaveModel.load_latest() == '{"a": 1}'


def test_second_save_replaces_previous():
    AutosaveModel.save("first")
    AutosaveModel.save("second")
    assert AutosaveModel.load_latest() == "second"


def test_only_one_row_after_many_saves():
    AutosaveModel.save("first")
    AutosaveModel.save("second")
    AutosaveModel.save("third")
    assert _count_rows() == 1
    assert AutosaveModel.load_latest() == "third"


def test_clear_removes_everything():
    AutosaveModel.save("x")
    AutosaveModel.clear()
    assert AutosaveModel.load_latest() is None
    assert _count_rows() == 0


# ---------------------------------------------------------------------
# Порядок операций: INSERT раньше DELETE
# ---------------------------------------------------------------------

class _RecordingCursor:
    def __init__(self, real, log):
        self._real = real
        self._log = log

    def execute(self, sql, parameters=()):
        self._log.append(sql.strip().upper())
        return self._real.execute(sql, parameters)

    def __getattr__(self, name):
        return getattr(self._real, name)


class _RecordingConnection:
    def __init__(self, real, log):
        self._real = real
        self._log = log

    def cursor(self):
        return _RecordingCursor(self._real.cursor(), self._log)

    def __getattr__(self, name):
        return getattr(self._real, name)


def test_insert_happens_before_delete(monkeypatch):
    """Сначала пишется новая копия, и только потом удаляется старая."""
    log = []
    import models.autosave_model as autosave_module

    real_get = get_connection
    monkeypatch.setattr(
        autosave_module, "get_connection",
        lambda: _RecordingConnection(real_get(), log),
    )

    AutosaveModel.save("payload")

    inserts = [i for i, s in enumerate(log) if s.startswith("INSERT INTO AUTOSAVE")]
    deletes = [i for i, s in enumerate(log) if s.startswith("DELETE FROM AUTOSAVE")]
    assert inserts, "не выполнена запись новой копии"
    assert deletes, "старые копии не удалены"
    assert inserts[0] < deletes[0]


# ---------------------------------------------------------------------
# Сбой записи новой копии не разрушает предыдущую
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


def test_failed_save_keeps_previous_copy(monkeypatch):
    AutosaveModel.save("OLD-COPY")

    import models.autosave_model as autosave_module

    real_get = get_connection
    monkeypatch.setattr(
        autosave_module, "get_connection",
        lambda: _InsertFailingConnection(real_get()),
    )

    with pytest.raises(RuntimeError):
        AutosaveModel.save("NEW-COPY")

    # Провалившаяся запись откатана — в базе осталась прежняя копия.
    assert AutosaveModel.load_latest() == "OLD-COPY"
