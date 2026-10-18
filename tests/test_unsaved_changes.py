# tests/test_unsaved_changes.py

"""Защита несохранённых данных и жизненный цикл автосохранения.

GUI-тесты: имитируют ответы пользователя в диалогах Save/Discard/Cancel
и проверяют, что текущий проект не теряется и не заменяется.
"""

import pytest
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtGui import QCloseEvent

from models.project_model import ProjectModel
from models.autosave_model import AutosaveModel
from views.main_window import MainWindow
from controllers.undo_commands import CellEditCommand
from utils import storage


@pytest.fixture(autouse=True)
def _clean_autosave():
    AutosaveModel.clear()
    yield
    AutosaveModel.clear()


@pytest.fixture
def window(qapp, monkeypatch):
    """Главное окно без запросов при создании и без реальных диалогов."""
    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *a, **k: QMessageBox.No))
    monkeypatch.setattr(QMessageBox, "warning",
                        staticmethod(lambda *a, **k: QMessageBox.Ok))
    monkeypatch.setattr(QMessageBox, "critical",
                        staticmethod(lambda *a, **k: QMessageBox.Ok))
    monkeypatch.setattr(QMessageBox, "information",
                        staticmethod(lambda *a, **k: QMessageBox.Ok))
    return MainWindow()


def _answer(monkeypatch, value):
    """Подменяет ответ пользователя в диалоге Save/Discard/Cancel."""
    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *a, **k: value))


def _load_project(window, path=None, dirty=False):
    """Загружает проект так, как это делает open_project/new_project."""
    m = ProjectModel(month=0, year=2025)
    m.add_employee("Иванов", "permanent")
    window._apply_model(m)
    window.current_file = str(path) if path else None
    window.project_model.mark_clean()
    window.undo_stack.setClean()
    if dirty:
        cmd = CellEditCommand(window.controller, 0, 2, "", "З")
        window.undo_stack.push(cmd)
    return window


# ---------------------------------------------------------------------
# Определение несохранённых изменений
# ---------------------------------------------------------------------

def test_no_project_has_no_unsaved_changes(window):
    assert window._has_unsaved_changes() is False


def test_saved_clean_project_has_no_unsaved_changes(window, tmp_path):
    _load_project(window, path=tmp_path / "p.json")
    assert window._has_unsaved_changes() is False


def test_new_project_without_file_is_unsaved(window):
    _load_project(window, path=None)
    # даже без правок проект без файла считается несохранённым
    assert window._has_unsaved_changes() is True


def test_dirty_saved_project_is_unsaved(window, tmp_path):
    _load_project(window, path=tmp_path / "p.json", dirty=True)
    assert window._has_unsaved_changes() is True


def test_clean_project_after_undo_is_unsaved_false(window, tmp_path):
    _load_project(window, path=tmp_path / "p.json", dirty=True)
    window.undo_stack.undo()
    assert window._has_unsaved_changes() is False


# ---------------------------------------------------------------------
# _maybe_save_changes: Save / Discard / Cancel
# ---------------------------------------------------------------------

def test_maybe_save_cancel_returns_false(window, tmp_path, monkeypatch):
    _load_project(window, path=tmp_path / "p.json", dirty=True)
    _answer(monkeypatch, QMessageBox.Cancel)
    assert window._maybe_save_changes() is False
    # проект не изменён
    assert window._has_unsaved_changes() is True


def test_maybe_save_discard_clears_autosave(window, tmp_path, monkeypatch):
    _load_project(window, path=tmp_path / "p.json", dirty=True)
    AutosaveModel.save(window.project_model.to_json())
    window._autosave_timer.start()
    _answer(monkeypatch, QMessageBox.Discard)
    assert window._maybe_save_changes() is True
    assert AutosaveModel.load_latest() is None
    assert not window._autosave_timer.isActive()


def test_maybe_save_save_writes_file(window, tmp_path, monkeypatch):
    path = tmp_path / "p.json"
    _load_project(window, path=path, dirty=True)
    _answer(monkeypatch, QMessageBox.Save)
    assert window._maybe_save_changes() is True
    assert path.exists()
    assert window._has_unsaved_changes() is False
    assert AutosaveModel.load_latest() is None


def test_save_failure_returns_false(window, tmp_path, monkeypatch):
    _load_project(window, path=tmp_path / "p.json", dirty=True)
    monkeypatch.setattr(storage, "save_model_to_file",
                        lambda model, path: False)
    _answer(monkeypatch, QMessageBox.Save)
    assert window._maybe_save_changes() is False
    assert window._has_unsaved_changes() is True


def test_save_as_cancel_keeps_current_file(window, monkeypatch):
    _load_project(window, path=None, dirty=True)
    monkeypatch.setattr(storage, "ask_save_path", lambda parent, name=None: None)
    _answer(monkeypatch, QMessageBox.Save)
    assert window._maybe_save_changes() is False
    assert window.current_file is None


def test_save_pending_timer_does_not_resurrect_autosave(window, tmp_path):
    """После обычного сохранения отложенный таймер не должен восстанавливать запись."""
    path = tmp_path / "p.json"
    _load_project(window, path=path, dirty=True)
    window._on_model_changed()               # запускает таймер
    assert window._autosave_timer.isActive()
    assert window.save_project() is True
    assert not window._autosave_timer.isActive()
    assert AutosaveModel.load_latest() is None


def test_apply_model_stops_pending_timer(window, tmp_path):
    _load_project(window, path=tmp_path / "p.json", dirty=True)
    window._on_model_changed()
    assert window._autosave_timer.isActive()
    window._apply_model(ProjectModel(month=1, year=2025))
    assert not window._autosave_timer.isActive()


# ---------------------------------------------------------------------
# new_project / open_project не теряют текущий проект
# ---------------------------------------------------------------------

def test_new_project_cancel_prompt_keeps_current_project(
        window, tmp_path, monkeypatch):
    """Мастер принят, но в диалоге сохранения выбран «Отмена».

    Подготовительное действие (мастер) выполняется до вопроса о
    несохранённых изменениях, поэтому «Отмена» оставляет текущий проект
    и его автосохранение без изменений.
    """
    _load_project(window, path=tmp_path / "p.json", dirty=True)
    original = window.project_model
    AutosaveModel.save(window.project_model.to_json())
    snapshot = AutosaveModel.load_latest()

    import views.main_window as mw

    class AcceptedWizard:
        Accepted = 1
        Rejected = 0

        def __init__(self, *a, **k):
            pass

        def exec_(self):
            return self.Accepted

        def get_result(self):
            return (1, 2025, [])

    monkeypatch.setattr(mw, "NewProjectWizard", AcceptedWizard)
    _answer(monkeypatch, QMessageBox.Cancel)

    window.new_project()

    assert window.project_model is original
    assert window.current_file == str(tmp_path / "p.json")
    assert AutosaveModel.load_latest() == snapshot


def test_open_project_cancel_prompt_keeps_current_project(
        window, tmp_path, monkeypatch):
    """Файл выбран и загружен, но в диалоге сохранения выбрана «Отмена».

    Переключение не выполняется: текущая модель, файл и автосохранение
    остаются прежними.
    """
    path = tmp_path / "p.json"
    _load_project(window, path=path, dirty=True)
    original = window.project_model
    AutosaveModel.save(window.project_model.to_json())
    snapshot = AutosaveModel.load_latest()

    new_file = tmp_path / "new.json"
    new_model = ProjectModel(month=1, year=2025)
    new_model.add_employee("Петров", "permanent")
    assert storage.save_model_to_file(new_model, str(new_file))

    monkeypatch.setattr(storage, "ask_open_path", lambda parent: str(new_file))
    _answer(monkeypatch, QMessageBox.Cancel)

    window.open_project()

    assert window.project_model is original
    assert window.current_file == str(path)
    assert AutosaveModel.load_latest() == snapshot


# ---------------------------------------------------------------------
# closeEvent
# ---------------------------------------------------------------------

def test_close_event_clean_accepts_and_clears_autosave(window, tmp_path):
    _load_project(window, path=tmp_path / "p.json")
    AutosaveModel.save(window.project_model.to_json())
    event = QCloseEvent()
    window.closeEvent(event)
    assert event.isAccepted()
    assert AutosaveModel.load_latest() is None


def test_close_event_cancel_ignores(window, tmp_path, monkeypatch):
    _load_project(window, path=tmp_path / "p.json", dirty=True)
    _answer(monkeypatch, QMessageBox.Cancel)
    event = QCloseEvent()
    window.closeEvent(event)
    assert not event.isAccepted()


def test_close_event_new_project_prompts_and_saves(window, tmp_path, monkeypatch):
    path = tmp_path / "new.json"
    _load_project(window, path=None)
    monkeypatch.setattr(storage, "ask_save_path",
                        lambda parent, name=None: str(path))
    _answer(monkeypatch, QMessageBox.Save)
    event = QCloseEvent()
    window.closeEvent(event)
    assert event.isAccepted()
    assert path.exists()


def test_close_event_discard_clears_autosave(window, tmp_path, monkeypatch):
    _load_project(window, path=tmp_path / "p.json", dirty=True)
    AutosaveModel.save(window.project_model.to_json())
    _answer(monkeypatch, QMessageBox.Discard)
    event = QCloseEvent()
    window.closeEvent(event)
    assert event.isAccepted()
    assert AutosaveModel.load_latest() is None


# ---------------------------------------------------------------------
# Повреждённое автосохранение
# ---------------------------------------------------------------------

def test_corrupt_autosave_shows_message_and_continues(window, monkeypatch):
    AutosaveModel.save("{ не json")
    _answer(monkeypatch, QMessageBox.Yes)   # пользователь согласился восстановить
    shown = {"n": 0}
    monkeypatch.setattr(QMessageBox, "warning",
                        staticmethod(lambda *a, **k: shown.__setitem__("n", shown["n"] + 1)))
    # не должно бросать исключение
    window._try_restore_autosave()
    assert shown["n"] == 1
    assert AutosaveModel.load_latest() is None


def test_autosave_db_error_does_not_crash(window, monkeypatch):
    def boom():
        raise RuntimeError("db broken")

    monkeypatch.setattr(AutosaveModel, "load_latest", staticmethod(boom))
    shown = {"n": 0}
    monkeypatch.setattr(QMessageBox, "warning",
                        staticmethod(lambda *a, **k: shown.__setitem__("n", shown["n"] + 1)))
    window._try_restore_autosave()
    assert shown["n"] == 1
