"""Модульные тесты модуля ввода (чёрный ящик).

Методы: эквивалентное разбиение и анализ граничных значений.
Классы эквивалентности размерности:

* допустимые целые 1..MAX_DIM;
* число вне диапазона;
* не целое число / не число;
* пустая строка.

Границы: 0, 1, MAX_DIM, MAX_DIM + 1.
"""
import math

import pytest

import input_module
import protocol
from errors import InputDataError
from helpers import Reader

pytestmark = pytest.mark.unit

MAX_DIM = protocol.MAX_DIM


# ---------------------------------------------------------------- parse_size
@pytest.mark.parametrize("text, expected", [
    ("1", 1),            # нижняя граница
    ("1000", MAX_DIM),   # верхняя граница
    ("5", 5),            # типичное значение
    (" 7 ", 7),          # пробелы по краям
    ("007", 7),          # ведущие нули
    ("+3", 3),           # явный знак «+»
])
def test_parse_size_accepts_valid_values(text, expected):
    assert input_module.parse_size(text, "n") == expected


@pytest.mark.parametrize("text", [
    "0",                 # ниже нижней границы
    str(MAX_DIM + 1),    # выше верхней границы
    "-1",                # отрицательное
    "1.5",               # не целое
    "abc",               # не число
    "",                  # пустая строка
    "   ",               # только пробелы
    "1 2",               # два числа
])
def test_parse_size_rejects_invalid_values(text):
    with pytest.raises(InputDataError):
        input_module.parse_size(text, "n")


def test_parse_size_reports_field_name():
    with pytest.raises(InputDataError) as error:
        input_module.parse_size("abc", "m")
    assert "m" in str(error.value)


# ---------------------------------------------------------------- parse_row
@pytest.mark.parametrize("text, expected", [
    ("1 2 3", [1.0, 2.0, 3.0]),
    ("0", [0.0]),
    ("-0", [-0.0]),
    ("1,5 0", [1.5, 0.0]),          # десятичная запятая
    ("  1   2  ", [1.0, 2.0]),      # лишние пробелы
    ("1e3 -2.5", [1000.0, -2.5]),   # экспоненциальная запись
    ("+4 -.5", [4.0, -0.5]),
])
def test_parse_row_accepts_valid_values(text, expected):
    row = input_module.parse_row(text, len(expected), 1)
    assert row == expected


def test_parse_row_negative_zero_is_zero():
    row = input_module.parse_row("-0", 1, 1)
    assert row[0] == 0 and math.copysign(1, row[0]) == -1


@pytest.mark.parametrize("text, width", [
    ("1 2", 3),          # меньше элементов
    ("1 2 3 4", 3),      # больше элементов
    ("", 1),             # пустая строка
    ("   ", 2),          # только пробелы
])
def test_parse_row_rejects_wrong_length(text, width):
    with pytest.raises(InputDataError):
        input_module.parse_row(text, width, 1)


@pytest.mark.parametrize("token", [
    "abc", "1..2", "1,2,3", "--1", "0x10", "e5",
])
def test_parse_row_rejects_non_numbers(token):
    with pytest.raises(InputDataError):
        input_module.parse_row(token, 1, 1)


@pytest.mark.parametrize("token", [
    "nan", "NaN", "inf", "-inf", "1e999", "-1e999",
])
def test_parse_row_rejects_non_finite_values(token):
    with pytest.raises(InputDataError):
        input_module.parse_row(token, 1, 1)


def test_parse_row_error_contains_row_index():
    with pytest.raises(InputDataError) as error:
        input_module.parse_row("abc", 1, 4)
    assert "строка 4" in str(error.value)


# -------------------------------------------------------------- read_matrix
def test_read_matrix_single_cell():
    data = input_module.read_matrix(Reader(["1", "1", "0"]))
    assert (data.n, data.m) == (1, 1)
    assert data.matrix == [[0.0]]


def test_read_matrix_typical():
    reader = Reader(["2", "3", "1 0 2", "3 4 5"])
    data = input_module.read_matrix(reader)
    assert (data.n, data.m) == (2, 3)
    assert data.matrix == [[1.0, 0.0, 2.0], [3.0, 4.0, 5.0]]


def test_read_matrix_reads_only_declared_rows():
    reader = Reader(["1", "1", "0", "лишняя строка"])
    data = input_module.read_matrix(reader)
    assert len(data.matrix) == 1
    assert reader.lines == ["лишняя строка"]


def test_read_matrix_eof_on_size():
    with pytest.raises(InputDataError):
        input_module.read_matrix(Reader([]))


def test_read_matrix_eof_on_row():
    with pytest.raises(InputDataError):
        input_module.read_matrix(Reader(["2", "2", "1 2"]))


def test_read_matrix_propagates_row_error():
    reader = Reader(["1", "2", "1 abc"])
    with pytest.raises(InputDataError):
        input_module.read_matrix(reader)


def test_ask_converts_eof():
    def failing(prompt):
        raise EOFError

    with pytest.raises(InputDataError):
        input_module._ask(failing, "> ")


def test_ask_returns_answer():
    calls = []
    answer = input_module._ask(lambda prompt: calls.append(prompt) or "42",
                               "> ")
    assert answer == "42"
    assert calls == ["> "]
