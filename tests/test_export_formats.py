# tests/test_export_formats.py

"""Экспорт графика для месяцев с 28, 29, 30 и 31 днём.

Проверяем, что ни один день/сотрудник/столбец не теряется, служебные
строки и примечания на месте, а выходные окрашены одинаково
в HTML, Excel и Word.
"""

import calendar

import pytest

from models.project_model import ProjectModel
from controllers.export_controller import (
    _collect_data, build_html, write_excel_file, write_word_file,
)

from docx import Document
from docx.oxml.ns import qn
from openpyxl import load_workbook


# (month, year, ожидаемое число дней)
CASES = [
    (0, 2025, 31),   # январь
    (1, 2025, 28),   # февраль, не високосный
    (1, 2024, 29),   # февраль, високосный
    (3, 2025, 30),   # апрель
]


def _make_model(month, year):
    m = ProjectModel(month=month, year=year)
    m.add_employee("Иванов И.И.", "permanent")
    m.add_employee("Петров П.П.", "parttime")
    m.set_note(0, "отпуск")
    return m


def _weekend_and_weekday(month, year):
    days = calendar.monthrange(year, month + 1)[1]
    weekends = [d for d in range(1, days + 1)
                if calendar.weekday(year, month + 1, d) in (5, 6)]
    weekdays = [d for d in range(1, days + 1)
                if calendar.weekday(year, month + 1, d) not in (5, 6)]
    return weekends, weekdays


def _cell_fill(cell):
    tcPr = cell._tc.tcPr
    if tcPr is None:
        return None
    shd = tcPr.find(qn('w:shd'))
    return None if shd is None else shd.get(qn('w:fill'))


# ---------------------------------------------------------------------
# Сбор данных
# ---------------------------------------------------------------------

@pytest.mark.parametrize("month, year, expected_days", CASES)
def test_collect_data_day_count(month, year, expected_days):
    m = _make_model(month, year)
    data = _collect_data(m)
    assert data['days'] == expected_days
    assert len(data['employees']) == 2
    assert data['employees'][0]['name'] == "Иванов И.И."


# ---------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------

@pytest.mark.parametrize("month, year, expected_days", CASES)
def test_html_contains_everything(month, year, expected_days):
    m = _make_model(month, year)
    html = build_html(m, scale=8)

    assert "Иванов И.И." in html
    assert "Петров П.П." in html
    assert ">Э<" in html and ">О<" in html
    assert "отпуск" in html
    # Последний день месяца присутствует в заголовке
    assert f">{expected_days}<br>" in html
    # Каждая дневная ячейка строки сотрудника присутствует
    for d in range(1, expected_days + 1):
        assert f">{d}<br>" in html


@pytest.mark.parametrize("month, year, expected_days", CASES)
def test_html_weekend_shading(month, year, expected_days):
    m = _make_model(month, year)
    weekends, weekdays = _weekend_and_weekday(month, year)
    html = build_html(m, scale=8)
    wd = weekends[0]
    wk = weekdays[0]
    assert f"<th class='shade'>{wd}<br>" in html
    assert f"<th class=''>{wk}<br>" in html


def test_html_weekend_duty_dark():
    # Январь 2025: 4 — суббота
    m = _make_model(0, 2025)
    m.employees[0]["duty_home"][3] = True
    html = build_html(m, scale=8)
    assert "duty-dark" in html


# ---------------------------------------------------------------------
# Excel
# ---------------------------------------------------------------------

@pytest.mark.parametrize("month, year, expected_days", CASES)
def test_excel_columns_and_content(tmp_path, month, year, expected_days):
    m = _make_model(month, year)
    path = tmp_path / "s.xlsx"
    write_excel_file(m, str(path), scale=8)
    wb = load_workbook(str(path))
    ws = wb.active

    # № + ФИО + дни
    assert ws.max_column == expected_days + 2
    assert ws.cell(row=3, column=1).value == "№"
    assert ws.cell(row=3, column=2).value == "ФИО"
    # Заголовок последнего дня
    assert str(ws.cell(row=3, column=2 + expected_days).value).startswith(
        str(expected_days)
    )
    # Сотрудники в первых строках данных
    assert ws.cell(row=4, column=2).value == "Иванов И.И."
    assert ws.cell(row=5, column=2).value == "Петров П.П."
    # Служебные строки и примечания
    assert ws.cell(row=6, column=2).value == "Э"
    assert ws.cell(row=7, column=2).value == "О"
    assert ws.cell(row=8, column=3).value == "отпуск"


@pytest.mark.parametrize("month, year, expected_days", CASES)
def test_excel_weekend_shading(tmp_path, month, year, expected_days):
    m = _make_model(month, year)
    weekends, weekdays = _weekend_and_weekday(month, year)
    path = tmp_path / "s.xlsx"
    write_excel_file(m, str(path), scale=8)
    ws = load_workbook(str(path)).active

    wd = weekends[0]
    wk = weekdays[0]
    weekend_fill = ws.cell(row=4, column=2 + wd).fill.start_color.rgb
    weekday_fill = ws.cell(row=4, column=2 + wk).fill
    assert weekend_fill and weekend_fill.endswith("CCCCCC")
    # Будний день без дежурства — без заливки
    assert weekday_fill.patternType is None


def test_excel_weekend_duty_dark(tmp_path):
    m = _make_model(0, 2025)
    m.employees[0]["duty_home"][3] = True   # 4 января — суббота
    path = tmp_path / "s.xlsx"
    write_excel_file(m, str(path), scale=8)
    ws = load_workbook(str(path)).active
    assert ws.cell(row=4, column=2 + 4).fill.start_color.rgb.endswith("969696")


# ---------------------------------------------------------------------
# Word
# ---------------------------------------------------------------------

@pytest.mark.parametrize("month, year, expected_days", CASES)
def test_word_table_dimensions(tmp_path, month, year, expected_days):
    m = _make_model(month, year)
    path = tmp_path / "s.docx"
    write_word_file(m, str(path), scale=8)
    table = Document(str(path)).tables[0]
    # шапка + 2 сотрудника + Э + О + примечания
    assert len(table.rows) == 2 + 4
    assert len(table.columns) == expected_days + 2
    assert table.rows[1].cells[1].text == "Иванов И.И."
    assert table.rows[2].cells[1].text == "Петров П.П."
    assert table.rows[-3].cells[1].text == "Э"
    assert table.rows[-2].cells[1].text == "О"
    assert table.rows[-1].cells[2].text == "отпуск"
    # Последний столбец не потерян
    assert table.rows[0].cells[-1].text.split("\n")[0] == str(expected_days)


@pytest.mark.parametrize("month, year, expected_days", CASES)
def test_word_weekend_shading(tmp_path, month, year, expected_days):
    m = _make_model(month, year)
    weekends, weekdays = _weekend_and_weekday(month, year)
    path = tmp_path / "s.docx"
    write_word_file(m, str(path), scale=8)
    table = Document(str(path)).tables[0]
    cells = table.rows[1].cells
    wd = weekends[0]
    wk = weekdays[0]
    assert _cell_fill(cells[1 + wd]) == "CCCCCC"
    assert _cell_fill(cells[1 + wk]) is None


# ---------------------------------------------------------------------
# PDF (печать)
# ---------------------------------------------------------------------

@pytest.mark.parametrize("month, year, expected_days", CASES)
def test_pdf_generation(qapp, tmp_path, month, year, expected_days):
    """Печать в PDF работает для месяцев с 28, 29, 30 и 31 днём.

    Повторяет конвейер export_pdf (build_html → QTextDocument → QPrinter)
    без диалогов. Формат печати при этом не меняется.
    """
    from PyQt5.QtGui import QTextDocument
    from PyQt5.QtPrintSupport import QPrinter

    m = _make_model(month, year)
    html = build_html(m, scale=8)
    path = tmp_path / "s.pdf"

    doc = QTextDocument()
    doc.setHtml(html)

    printer = QPrinter(QPrinter.HighResolution)
    printer.setOutputFormat(QPrinter.PdfFormat)
    printer.setOutputFileName(str(path))
    printer.setOrientation(QPrinter.Landscape)
    printer.setPageMargins(10, 10, 10, 10, QPrinter.Millimeter)

    doc.print_(printer)

    assert path.exists()
    assert path.stat().st_size > 0
    assert path.read_bytes()[:4] == b"%PDF"
