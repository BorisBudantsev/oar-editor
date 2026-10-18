# tests/test_build_config.py

"""Сборка и конфигурация: кодировка требований, spec-файлы, роли.

Проверяем то, что легко сломать при правках и что не видно из обычных
тестов логики: кодировку requirements.txt, наличие ресурсов и скрытых
импортов в spec-файлах, определение роли (два независимых приложения).
"""

import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------
# requirements.txt
# ---------------------------------------------------------------------

def test_requirements_is_utf8_without_bom():
    raw = (PROJECT_ROOT / "requirements.txt").read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf"), "найден UTF-8 BOM"
    assert not raw.startswith(b"\xff\xfe"), "найден UTF-16LE BOM"
    assert not raw.startswith(b"\xfe\xff"), "найден UTF-16BE BOM"
    text = raw.decode("utf-8")   # не должно бросать UnicodeDecodeError
    assert text.strip(), "requirements.txt пуст"


@pytest.mark.parametrize(
    "package", ["PyQt5", "openpyxl", "python-docx", "pyinstaller", "pytest"]
)
def test_requirements_lists_key_packages(package):
    text = (PROJECT_ROOT / "requirements.txt").read_text(encoding="utf-8")
    assert package.lower() in text.lower()


# ---------------------------------------------------------------------
# spec-файлы PyInstaller
# ---------------------------------------------------------------------

SPECS = [
    ("OAR_Doctors.spec", "OAR_Doctors", "assets/app_doctors.ico"),
    ("OAR_Nurses.spec", "OAR_Nurses", "assets/app_nurses.ico"),
]

HIDDEN_IMPORTS = ["PyQt5.QtSvg", "PyQt5.QtPrintSupport", "openpyxl", "docx"]


@pytest.mark.parametrize("spec_name,exe_name,icon", SPECS)
def test_spec_declares_exe_resources_and_icon(spec_name, exe_name, icon):
    text = (PROJECT_ROOT / spec_name).read_text(encoding="utf-8")
    assert f"name='{exe_name}'" in text
    assert icon in text
    assert "('assets', 'assets')" in text


@pytest.mark.parametrize("spec_name,exe_name,icon", SPECS)
@pytest.mark.parametrize("hidden", HIDDEN_IMPORTS)
def test_spec_declares_hidden_import(spec_name, exe_name, icon, hidden):
    text = (PROJECT_ROOT / spec_name).read_text(encoding="utf-8")
    assert hidden in text


def test_specs_produce_two_distinct_executables():
    doctors = (PROJECT_ROOT / "OAR_Doctors.spec").read_text(encoding="utf-8")
    nurses = (PROJECT_ROOT / "OAR_Nurses.spec").read_text(encoding="utf-8")
    assert "name='OAR_Doctors'" in doctors
    assert "name='OAR_Nurses'" not in doctors
    assert "name='OAR_Nurses'" in nurses
    assert "name='OAR_Doctors'" not in nurses


# ---------------------------------------------------------------------
# Определение роли (два независимых приложения)
# ---------------------------------------------------------------------

def test_detect_role_default_is_doctor(monkeypatch):
    import app_config
    monkeypatch.delattr(sys, "frozen", raising=False)
    monkeypatch.setattr(sys, "argv", ["main.py"])
    assert app_config.detect_role() == "doctor"


def test_detect_role_nurse_by_exe_name(monkeypatch):
    import app_config
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", r"C:\Apps\OAR_Nurses.exe")
    monkeypatch.setattr(sys, "argv", [r"C:\Apps\OAR_Nurses.exe"])
    assert app_config.detect_role() == "nurse"


def test_detect_role_doctor_by_exe_name(monkeypatch):
    import app_config
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", r"C:\Apps\OAR_Doctors.exe")
    monkeypatch.setattr(sys, "argv", [r"C:\Apps\OAR_Doctors.exe"])
    assert app_config.detect_role() == "doctor"


def test_detect_role_nurse_by_argument(monkeypatch):
    import app_config
    monkeypatch.delattr(sys, "frozen", raising=False)
    monkeypatch.setattr(sys, "argv", ["main.py", "--role", "nurse"])
    assert app_config.detect_role() == "nurse"


def test_detect_role_argument_has_priority_over_exe(monkeypatch):
    import app_config
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", r"C:\Apps\OAR_Nurses.exe")
    monkeypatch.setattr(sys, "argv", ["main.py", "--role", "doctor"])
    assert app_config.detect_role() == "doctor"


def test_detect_role_ignores_unknown_argument(monkeypatch):
    import app_config
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", r"C:\Apps\OAR_Nurses.exe")
    monkeypatch.setattr(sys, "argv", ["main.py", "--role", "boss"])
    assert app_config.detect_role() == "nurse"


# ---------------------------------------------------------------------
# Независимость двух приложений
# ---------------------------------------------------------------------

def test_two_roles_use_independent_data_folders():
    from app_config import CONFIG, ROLE_DOCTOR, ROLE_NURSE
    assert CONFIG[ROLE_DOCTOR]["data_folder"] == "OAR_Doctors"
    assert CONFIG[ROLE_NURSE]["data_folder"] == "OAR_Nurses"
    assert CONFIG[ROLE_DOCTOR]["data_folder"] != CONFIG[ROLE_NURSE]["data_folder"]


def test_two_roles_have_different_titles_and_filenames():
    from app_config import CONFIG, ROLE_DOCTOR, ROLE_NURSE
    d, n = CONFIG[ROLE_DOCTOR], CONFIG[ROLE_NURSE]
    assert d["app_title"] != n["app_title"]
    assert d["project_filename"] != n["project_filename"]
    assert d["export_filename"] != n["export_filename"]
