# tests/test_undo_dirty.py

"""Отслеживание «контрольной точки» undo-стека.

Проект считается несохранённым только пока текущее состояние отличается
от последней сохранённой/открытой контрольной точки. Полный Undo всех
правок должен снова делать проект «чистым», Redo — снова «грязным».
"""

import pytest
from PyQt5.QtWidgets import QMessageBox

from models.project_model import ProjectModel
from models.autosave_model import AutosaveModel
from views.main_window import MainWindow
from controllers.undo_commands import CellEditCommand, DutyHomeCommand


@pytest.fixture(autouse=True)
def _clean_autosave():
    AutosaveModel.clear()
    yield
    AutosaveModel.clear()


@pytest.fixture
def window(qapp, monkeypatch):
    """Пустое окно без реальных диалогов и без восстановления автосейва."""
    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *a, **k: QMessageBox.No))
    monkeypatch.setattr(QMessageBox, "warning",
                        staticmethod(lambda *a, **k: QMessageBox.Ok))
    monkeypatch.setattr(QMessageBox, "critical",
                        staticmethod(lambda *a, **k: QMessageBox.Ok))
    monkeypatch.setattr(QMessageBox, "information",
                        staticmethod(lambda *a, **k: QMessageBox.Ok))
    return MainWindow()


def _saved_project(window, path):
    """Загружает проект и помечает сохранённую контрольную точку.

    Повторяет то, что делает open_project: применяет модель и вызывает
    mark_clean() + undo_stack.setClean().
    """
    m = ProjectModel(month=0, year=2025)
    m.add_employee("Иванов", "permanent")
    window._apply_model(m)
    window.current_file = str(path)
    window.project_model.mark_clean()
    window.undo_stack.setClean()


def _new_project(window):
    """Проект без файла (как после new_project)."""
    m = ProjectModel(month=0, year=2025)
    m.add_employee("Иванов", "permanent")
    window._apply_model(m)
    window.current_file = None
    window.project_model.mark_clean()
    window.undo_stack.setClean()


def _row_of(window, kind, key=None):
    """Индекс строки таблицы по её типу (и ключу для служебных строк)."""
    for i, (rtype, data) in enumerate(window.controller.row_map):
        if rtype == kind and (key is None or data == key):
            return i
    raise AssertionError(f"строка {kind}/{key} не найдена")


def _edit_cell(window, row, col, old, new):
    window.undo_stack.push(
        CellEditCommand(window.controller, row, col, old, new)
    )


def _toggle_duty(window, row, col, old, new):
    window.undo_stack.push(
        DutyHomeCommand(window.controller, row, col, old, new)
    )


# ---------------------------------------------------------------------
# Полный Undo возвращает «чистое» состояние
# ---------------------------------------------------------------------

def test_fresh_saved_project_is_clean(window, tmp_path):
    _saved_project(window, tmp_path / "p.json")
    assert window._has_unsaved_changes() is False


def test_employee_cell_undo_returns_to_clean(window, tmp_path):
    _saved_project(window, tmp_path / "p.json")
    row = _row_of(window, 'employee')
    _edit_cell(window, row, 2, "", "З")
    assert window.project_model.employees[0]["days"][0] == "З"
    assert window._has_unsaved_changes() is True
    window.undo_stack.undo()
    assert window.project_model.employees[0]["days"][0] == ""
    assert window._has_unsaved_changes() is False


def test_special_cell_undo_returns_to_clean(window, tmp_path):
    _saved_project(window, tmp_path / "p.json")
    row = _row_of(window, 'special', 'Э')
    _edit_cell(window, row, 2, "3", "1")
    assert window.project_model.special["Э"][0] == "1"
    assert window._has_unsaved_changes() is True
    window.undo_stack.undo()
    assert window.project_model.special["Э"][0] == "3"
    assert window._has_unsaved_changes() is False


def test_notes_undo_returns_to_clean(window, tmp_path):
    _saved_project(window, tmp_path / "p.json")
    row = _row_of(window, 'notes')
    _edit_cell(window, row, 2, "", "отпуск")
    assert window.project_model.notes[0] == "отпуск"
    assert window._has_unsaved_changes() is True
    window.undo_stack.undo()
    assert window.project_model.notes[0] == ""
    assert window._has_unsaved_changes() is False


def test_duty_home_undo_returns_to_clean(window, tmp_path):
    _saved_project(window, tmp_path / "p.json")
    row = _row_of(window, 'employee')
    _toggle_duty(window, row, 2, False, True)
    assert window.project_model.employees[0]["duty_home"][0] is True
    assert window._has_unsaved_changes() is True
    window.undo_stack.undo()
    assert window.project_model.employees[0]["duty_home"][0] is False
    assert window._has_unsaved_changes() is False


# ---------------------------------------------------------------------
# Redo и частичный Undo
# ---------------------------------------------------------------------

def test_redo_after_undo_is_dirty_again(window, tmp_path):
    _saved_project(window, tmp_path / "p.json")
    row = _row_of(window, 'employee')
    _edit_cell(window, row, 2, "", "З")
    window.undo_stack.undo()
    assert window._has_unsaved_changes() is False
    window.undo_stack.redo()
    assert window._has_unsaved_changes() is True


def test_partial_undo_still_dirty(window, tmp_path):
    _saved_project(window, tmp_path / "p.json")
    row = _row_of(window, 'employee')
    _edit_cell(window, row, 2, "", "З")
    _edit_cell(window, row, 3, "", "Б")
    window.undo_stack.undo()   # отменяем только вторую правку
    assert window._has_unsaved_changes() is True


# ---------------------------------------------------------------------
# Контрольная точка сдвигается при сохранении
# ---------------------------------------------------------------------

def test_save_moves_clean_point(window, tmp_path):
    path = tmp_path / "p.json"
    _saved_project(window, path)
    row = _row_of(window, 'employee')
    _edit_cell(window, row, 2, "", "З")
    assert window.save_project() is True
    assert window._has_unsaved_changes() is False
    # правим ещё раз и отменяем — снова чисто относительно сохранённого файла
    _edit_cell(window, row, 2, "З", "Б")
    assert window._has_unsaved_changes() is True
    window.undo_stack.undo()
    assert window._has_unsaved_changes() is False


def test_new_project_without_file_stays_unsaved_after_undo(window):
    _new_project(window)
    row = _row_of(window, 'employee')
    _edit_cell(window, row, 2, "", "З")
    window.undo_stack.undo()
    # файла нет — проект всё ещё несохранён, несмотря на пустой undo-стек
    assert window._has_unsaved_changes() is True
