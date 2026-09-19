# tests/test_autosave.py

import json
import pytest

from models.autosave_model import AutosaveModel


@pytest.fixture(autouse=True)
def _clean_autosave():
    """Очищает таблицу autosave до и после каждого теста."""
    AutosaveModel.clear()
    yield
    AutosaveModel.clear()


def test_save_and_load():
    AutosaveModel.save('{"test": 1}')
    data = AutosaveModel.load_latest()
    assert data == '{"test": 1}'


def test_save_replaces_previous():
    AutosaveModel.save('{"n": 1}')
    AutosaveModel.save('{"n": 2}')
    data = AutosaveModel.load_latest()
    assert data == '{"n": 2}'


def test_load_when_empty():
    assert AutosaveModel.load_latest() is None


def test_clear():
    AutosaveModel.save('{"x": 1}')
    AutosaveModel.clear()
    assert AutosaveModel.load_latest() is None


def test_save_unicode():
    payload = json.dumps({"name": "Иванов И.И."}, ensure_ascii=False)
    AutosaveModel.save(payload)
    loaded = AutosaveModel.load_latest()
    assert loaded == payload
    parsed = json.loads(loaded)
    assert parsed["name"] == "Иванов И.И."