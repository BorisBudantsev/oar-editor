# tests/test_project_switch.py

"""Переключение проектов (создание / открытие).

Главный критерий: отменённое, неудачное или прерванное переключение не
должно изменять текущий проект, его файл и лишать пользователя уже
существующей аварийной копии (автосохранения).

Регрессия, которую фиксируют эти тесты: раньше диалог «Несохранённые
изменения» показывался ДО выбора файла / мастера нового проекта. Выбор
«Не сохранять» немедленно удалял автосохранение, и если после этого
пользователь отменял выбор файла (или мастер), исходный проект оставался
открытым, но уже без аварийной копии. Теперь подготовительное действие
выполняется раньше вопроса о сохранении.
"""

import json

import pytest
from PyQt5.QtWidgets import QMessageBox

from models.project_model import ProjectModel
from models.autosave_model import AutosaveModel
from views.main_window import MainWindow
from controllers.undo_commands import CellEditCommand, DutyHomeCommand
from utils import storage


UNSAVED_TITLE = "Несохранённые изменения"

# Заголовки всех показанных QMessageBox.question (заполняется _answer).
_ASKED = []


@pytest.fixture(autouse=True)
def _isolate_autosave():
    """Каждый тест начинается и заканчивается без аварийной копии."""
    AutosaveModel.clear()
    _ASKED.clear()
    yield
    AutosaveModel.clear()
    _ASKED.clear()


@pytest.fixture
def window(qapp, monkeypatch):
    """Главное окно без реальных модальных диалогов при создании."""
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
    """Задаёт ответ пользователя в диалоге Save/Discard/Cancel."""
    def fake(parent, title, text, *a, **k):
        _ASKED.append(title)
        return value
    monkeypatch.setattr(QMessageBox, "question", staticmethod(fake))


def _critical_spy(monkeypatch):
    """Перехватывает QMessageBox.critical и возвращает список заголовков."""
    seen = []

    def fake(parent, title, text, *a, **k):
        seen.append(title)
        return QMessageBox.Ok

    monkeypatch.setattr(QMessageBox, "critical", staticmethod(fake))
    return seen


def _current_project(window, path=None, dirty=False):
    """Готовит открытый проект так, как это делает приложение."""
    model = ProjectModel(month=0, year=2025)
    model.add_employee("Иванов", "permanent")
    window._apply_model(model)
    window.current_file = str(path) if path else None
    window.project_model.mark_clean()
    window.undo_stack.setClean()
    if dirty:
        window.undo_stack.push(
            CellEditCommand(window.controller, 0, 2, "", "З"))
    return window


def _snapshot_autosave(window):
    """Фиксирует текущее автосохранение и возвращает его снимок."""
    window._autosave_timer.stop()
    AutosaveModel.save(window.project_model.to_json())
    return AutosaveModel.load_latest()


def _write_valid_project(path, name="Петров"):
    """Создаёт корректный файл проекта — цель переключения."""
    model = ProjectModel(month=1, year=2025)
    model.add_employee(name, "permanent")
    assert storage.save_model_to_file(model, str(path))
    return model


class _Wizard:
    """Подменяет NewProjectWizard с заданным результатом exec_."""

    Accepted = 1
    Rejected = 0

    def __init__(self, result, *args, **kwargs):
        self._result = result

    def exec_(self):
        return self._result

    def get_result(self):
        if self._result != self.Accepted:
            raise AssertionError("результат не должен запрашиваться")
        return (1, 2025, [])   # февраль 2025, без сотрудников


def _rejected_wizard(monkeypatch):
    import views.main_window as mw
    monkeypatch.setattr(mw, "NewProjectWizard",
                        lambda *a, **k: _Wizard(_Wizard.Rejected))


def _accepted_wizard(monkeypatch):
    import views.main_window as mw
    monkeypatch.setattr(mw, "NewProjectWizard",
                        lambda *a, **k: _Wizard(_Wizard.Accepted))


# ---------------------------------------------------------------------
# 1. «Не сохранять» → отмена открытия файла: проект и автосейв целы
# ---------------------------------------------------------------------

def test_open_cancelled_file_dialog_keeps_project_and_autosave(
        window, tmp_path, monkeypatch):
    path = tmp_path / "p.json"
    _current_project(window, path, dirty=True)
    original = window.project_model
    snapshot = _snapshot_autosave(window)

    # Если бы вопрос задали ДО выбора файла, этот ответ стёр бы автосейв.
    _answer(monkeypatch, QMessageBox.Discard)
    monkeypatch.setattr(storage, "ask_open_path", lambda parent: None)

    window.open_project()

    assert window.project_model is original
    assert window.current_file == str(path)
    assert AutosaveModel.load_latest() == snapshot
    # Вопрос о сохранении не должен был задаваться вообще.
    assert UNSAVED_TITLE not in _ASKED


# ---------------------------------------------------------------------
# 2. «Не сохранять» → отмена мастера нового проекта
# ---------------------------------------------------------------------

def test_new_cancelled_wizard_keeps_project_and_autosave(
        window, tmp_path, monkeypatch):
    path = tmp_path / "p.json"
    _current_project(window, path, dirty=True)
    original = window.project_model
    snapshot = _snapshot_autosave(window)

    _rejected_wizard(monkeypatch)
    _answer(monkeypatch, QMessageBox.Discard)

    window.new_project()

    assert window.project_model is original
    assert window.current_file == str(path)
    assert AutosaveModel.load_latest() == snapshot
    assert UNSAVED_TITLE not in _ASKED


# ---------------------------------------------------------------------
# 3. «Не сохранять» → попытка открыть повреждённый JSON
# ---------------------------------------------------------------------

def test_open_corrupt_file_keeps_current_project(
        window, tmp_path, monkeypatch):
    path = tmp_path / "p.json"
    _current_project(window, path, dirty=True)
    original = window.project_model
    snapshot = _snapshot_autosave(window)

    bad = tmp_path / "bad.json"
    bad.write_text("{ это не json", encoding="utf-8")

    monkeypatch.setattr(storage, "ask_open_path", lambda parent: str(bad))
    _answer(monkeypatch, QMessageBox.Discard)
    errors = _critical_spy(monkeypatch)

    window.open_project()

    assert window.project_model is original
    assert window.current_file == str(path)
    assert AutosaveModel.load_latest() == snapshot
    assert errors                     # пользователю показана ошибка открытия
    assert UNSAVED_TITLE not in _ASKED


# ---------------------------------------------------------------------
# 4. «Сохранить» → отмена выбора пути: переключение не выполняется
# ---------------------------------------------------------------------

def test_save_then_cancel_path_aborts_switch(window, tmp_path, monkeypatch):
    # Проект без файла: «Сохранить» уйдёт в save-as и спросит путь.
    _current_project(window, None, dirty=True)
    original = window.project_model
    snapshot = _snapshot_autosave(window)

    new_file = tmp_path / "new.json"
    _write_valid_project(new_file)

    monkeypatch.setattr(storage, "ask_open_path", lambda parent: str(new_file))
    monkeypatch.setattr(storage, "ask_save_path",
                        lambda parent, name=None: None)   # отмена выбора пути
    _answer(monkeypatch, QMessageBox.Save)

    window.open_project()

    assert window.project_model is original
    assert window.current_file is None
    assert AutosaveModel.load_latest() == snapshot


# ---------------------------------------------------------------------
# 5. «Сохранить» → ошибка записи файла: переключение не выполняется
# ---------------------------------------------------------------------

def test_save_write_error_aborts_switch(window, tmp_path, monkeypatch):
    path = tmp_path / "p.json"
    _current_project(window, path, dirty=True)
    original = window.project_model
    snapshot = _snapshot_autosave(window)

    new_file = tmp_path / "new.json"
    _write_valid_project(new_file)

    monkeypatch.setattr(storage, "ask_open_path", lambda parent: str(new_file))
    monkeypatch.setattr(storage, "save_model_to_file",
                        lambda model, p: False)           # запись не удалась
    _answer(monkeypatch, QMessageBox.Save)

    window.open_project()

    assert window.project_model is original
    assert window.current_file == str(path)
    assert AutosaveModel.load_latest() == snapshot


# ---------------------------------------------------------------------
# 6. Правка ячейки → Undo до сохранённого состояния
# ---------------------------------------------------------------------

def test_cell_edit_undo_returns_to_clean(window, tmp_path):
    _current_project(window, tmp_path / "p.json")
    assert window._has_unsaved_changes() is False

    window.undo_stack.push(CellEditCommand(window.controller, 0, 2, "", "З"))
    assert window._has_unsaved_changes() is True

    window.undo_stack.undo()
    assert window._has_unsaved_changes() is False


# ---------------------------------------------------------------------
# 7. Правка дежурства на дому → Undo до сохранённого состояния
# ---------------------------------------------------------------------

def test_duty_home_undo_returns_to_clean(window, tmp_path):
    _current_project(window, tmp_path / "p.json")
    assert window._has_unsaved_changes() is False

    window.undo_stack.push(
        DutyHomeCommand(window.controller, 0, 2, False, True))
    assert window._has_unsaved_changes() is True

    window.undo_stack.undo()
    assert window._has_unsaved_changes() is False


# ---------------------------------------------------------------------
# 8. Успешное переключение → корректное состояние автосохранения
# ---------------------------------------------------------------------

def test_successful_open_clears_autosave(window, tmp_path, monkeypatch):
    path = tmp_path / "p.json"
    _current_project(window, path, dirty=True)
    _snapshot_autosave(window)

    new_file = tmp_path / "new.json"
    _write_valid_project(new_file, name="Петров")

    monkeypatch.setattr(storage, "ask_open_path", lambda parent: str(new_file))
    _answer(monkeypatch, QMessageBox.Discard)

    window.open_project()

    assert window.current_file == str(new_file)
    assert window.project_model.employees[0]["name"] == "Петров"
    # Файл только что открыт и не изменялся — аварийная копия не нужна.
    assert AutosaveModel.load_latest() is None


def test_successful_new_project_replaces_autosave(
        window, tmp_path, monkeypatch):
    _current_project(window, tmp_path / "p.json", dirty=True)
    _snapshot_autosave(window)

    _accepted_wizard(monkeypatch)
    _answer(monkeypatch, QMessageBox.Discard)

    window.new_project()

    assert window.current_file is None
    data = AutosaveModel.load_latest()
    assert data is not None
    assert json.loads(data)["month"] == 1


def test_save_then_successful_switch_writes_old_file(
        window, tmp_path, monkeypatch):
    path = tmp_path / "p.json"
    _current_project(window, path, dirty=True)

    new_file = tmp_path / "new.json"
    _write_valid_project(new_file, name="Петров")

    monkeypatch.setattr(storage, "ask_open_path", lambda parent: str(new_file))
    _answer(monkeypatch, QMessageBox.Save)

    window.open_project()

    assert window.current_file == str(new_file)
    assert window.project_model.employees[0]["name"] == "Петров"
    assert path.exists()   # старый проект действительно записан на диск


# ---------------------------------------------------------------------
# 9. Отмена переключения → модель, файл и автосохранение без изменений
# ---------------------------------------------------------------------

def test_cancel_unsaved_prompt_keeps_model_file_and_autosave(
        window, tmp_path, monkeypatch):
    path = tmp_path / "p.json"
    _current_project(window, path, dirty=True)
    original = window.project_model
    snapshot = _snapshot_autosave(window)

    new_file = tmp_path / "new.json"
    _write_valid_project(new_file, name="Петров")

    monkeypatch.setattr(storage, "ask_open_path", lambda parent: str(new_file))
    _answer(monkeypatch, QMessageBox.Cancel)

    window.open_project()

    assert window.project_model is original
    assert window.current_file == str(path)
    assert AutosaveModel.load_latest() == snapshot
    assert UNSAVED_TITLE in _ASKED


# ---------------------------------------------------------------------
# Условие корректности _has_unsaved_changes: правки идут через undo-стек
# ---------------------------------------------------------------------

def test_ui_edits_are_tracked_by_undo_stack(window, tmp_path):
    """Пользовательские правки обязаны попадать в QUndoStack.

    _has_unsaved_changes() опирается только на стек отмены, поэтому
    любая правка мимо стека была бы не замечена. Тест пинает инвариант:
    штатные операции пользователя увеличивают счётчик стека, а полный
    Undo возвращает проект в «чистое» состояние.
    """
    _current_project(window, tmp_path / "p.json")

    # Правка ячейки: делегат → cellChanged → on_cell_changed → CellEditCommand.
    item = window.table.item(0, 2)
    window.table.blockSignals(True)
    item.setText("З")
    window.table.blockSignals(False)
    window.on_cell_changed(0, 2)
    assert window.undo_stack.count() == 1   # правка легла в стек
    assert window._has_unsaved_changes() is True
    window.undo_stack.undo()
    assert window._has_unsaved_changes() is False

    # Новая контрольная точка для следующей проверки.
    window.undo_stack.clear()

    # Дежурство на дому: контекстное меню → _ctx_set_duty → DutyHomeCommand.
    window._ctx_set_duty(0, 2, True)
    assert window.undo_stack.count() == 1   # правка легла в стек
    assert window._has_unsaved_changes() is True
    window.undo_stack.undo()
    assert window._has_unsaved_changes() is False
