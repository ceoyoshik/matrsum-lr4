"""Модульные тесты модуля вывода (граничные значения и форматирование)."""
import pytest

import output_module
from mapping import OutputData

pytestmark = pytest.mark.unit


# ------------------------------------------------------------- format_number
@pytest.mark.parametrize("value, expected", [
    (0, "0.000"),
    (1, "1.000"),
    (1.5, "1.500"),
    (2.3456, "2.346"),        # округление вверх
    (2.3444, "2.344"),        # округление вниз
    (1234.5, "1234.500"),
    (-7.25, "-7.250"),
    (1e-7, "0.000"),          # меньше точности
])
def test_format_number_typical(value, expected):
    assert output_module.format_number(value) == expected


@pytest.mark.parametrize("value", [0.0, -0.0, -0.0004, -1e-9])
def test_format_number_never_prints_negative_zero(value):
    assert output_module.format_number(value) == "0.000"


def test_format_number_custom_precision():
    assert output_module.format_number(1.23456, precision=1) == "1.2"
    assert output_module.format_number(1.23456, precision=0) == "1"
    assert output_module.format_number(1.5, precision=5) == "1.50000"


def test_format_number_precision_boundary():
    assert output_module.format_number(0.00049, precision=3) == "0.000"
    assert output_module.format_number(0.00051, precision=3) == "0.001"


# ------------------------------------------------------------- format_result
def test_format_result_with_columns():
    text = output_module.format_result(OutputData((1, 3), 23.0))
    assert text == ("Столбцы с нулевым элементом: 1, 3\n"
                    "Сумма элементов этих столбцов: 23.000")


def test_format_result_single_column():
    text = output_module.format_result(OutputData((2,), 1.5))
    assert "2\n" in text
    assert "1.500" in text


def test_format_result_without_columns():
    text = output_module.format_result(OutputData((), 0.0))
    assert text == ("Столбцов с нулевым элементом нет.\n"
                    "Сумма элементов: 0.000")


def test_format_result_custom_precision():
    text = output_module.format_result(OutputData((1,), 2.0), precision=1)
    assert "2.0" in text


def test_format_result_negative_total():
    text = output_module.format_result(OutputData((1,), -0.0001))
    assert "0.000" in text


# ---------------------------------------------------------------------- show
def test_show_writes_formatted_result():
    written = []
    output_module.show(OutputData((1,), 5.0), written.append)
    assert written == ["Столбцы с нулевым элементом: 1\n"
                       "Сумма элементов этих столбцов: 5.000"]


def test_show_uses_print_by_default(capsys):
    output_module.show(OutputData((), 0.0))
    assert "Столбцов с нулевым элементом нет." in capsys.readouterr().out
