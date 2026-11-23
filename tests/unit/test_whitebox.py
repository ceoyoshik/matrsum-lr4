"""Тесты методов «белого ящика»: покрытие решений, условий и комбинаций.

Каждый тест соответствует строке таблицы из docs/testing.md:
критерий покрытия -> условия -> наборы данных.
"""
import pytest

import input_module
import processing_module
import protocol
from errors import InputDataError, ProtocolError, VersionConflictError

pytestmark = pytest.mark.whitebox


# ------------------------------------------------ покрытие условий is_number
# Решение: (isinstance(A) and not B) and isfinite(C)
CONDITION_TABLE = [
    # A: int/float, B: bool, C: конечное число, ожидаемый результат
    (1, False, True, True),
    (1.5, False, True, True),
    ("1", None, None, False),
    (None, None, None, False),
    (True, True, None, False),
    (False, True, None, False),
    (float("nan"), False, False, False),
    (float("inf"), False, False, False),
]


@pytest.mark.parametrize("value, is_bool, finite, expected", CONDITION_TABLE)
def test_is_number_condition_coverage(value, is_bool, finite, expected):
    assert protocol.is_number(value) is expected


# ------------------------------------- комбинаторное покрытие check_version
# Условия: S — version строка, L — две части, D — обе части из цифр,
# M — major совпадает с поддерживаемым.
VERSION_COMBINATIONS = [
    # S, L, D, M, ожидаемое исключение (None — версия принята)
    (True, True, True, True, None),
    (True, True, True, False, VersionConflictError),
    (True, True, False, None, ProtocolError),
    (True, False, None, None, ProtocolError),
    (False, None, None, None, ProtocolError),
]


@pytest.mark.parametrize("is_str, two_parts, digits, major, exception",
                         VERSION_COMBINATIONS)
def test_check_version_combinatorial(is_str, two_parts, digits, major,
                                     exception):
    if not is_str:
        version = 1
    elif not two_parts:
        version = "1"
    elif not digits:
        version = "1.a"
    elif major:
        version = "1.0"
    else:
        version = "2.0"
    if exception is None:
        protocol.check_version(version)
    else:
        with pytest.raises(exception):
            protocol.check_version(version)


# ----------------------------------------- покрытие решений validate_envelope
ENVELOPE_CASES = [
    # (сообщение, ожидаемый тип исключения)
    ("not a dict", ProtocolError),
    ({"type": "x", "payload": {}}, ProtocolError),
    ({"version": "1.0", "payload": {}}, ProtocolError),
    ({"version": "1.0", "type": "x"}, ProtocolError),
    ({"version": "2.0", "type": "x", "payload": {}}, VersionConflictError),
    ({"version": "1.0", "type": "x", "payload": []}, ProtocolError),
    ({"version": "1.0", "type": "x", "payload": {}, "extra": 1},
     ProtocolError),
]


@pytest.mark.parametrize("message, exception", ENVELOPE_CASES)
def test_validate_envelope_decision_coverage(message, exception):
    with pytest.raises(exception):
        protocol.validate_envelope(message, protocol.MSG_REQUEST)


# ------------------------------------------ покрытие условий parse_request
DIMENSION_CASES = [
    # (rows, cols, длина matrix, ожидаемый тип исключения)
    (1, 1, 1, None),
    (0, 1, 1, InputDataError),
    (1, 0, 1, InputDataError),
    (1001, 1, 1, InputDataError),
    (1, 1001, 1, InputDataError),
    (2, 1, 1, InputDataError),
]


@pytest.mark.parametrize("rows, cols, length, exception", DIMENSION_CASES)
def test_parse_request_dimension_conditions(rows, cols, length, exception):
    message = protocol.build_request(1, 1, [[0]])
    message["payload"].update(rows=rows, cols=cols,
                              matrix=[[0]] * length)
    if exception is None:
        assert protocol.parse_request(message) == [[0.0]]
    else:
        with pytest.raises(exception):
            protocol.parse_request(message)


@pytest.mark.parametrize("cell, exception", [
    (1, None),
    (1.5, None),
    (True, InputDataError),
    ("1", InputDataError),
    (None, InputDataError),
    (float("nan"), InputDataError),
])
def test_parse_request_cell_conditions(cell, exception):
    message = protocol.build_request(1, 1, [[0]])
    message["payload"]["matrix"] = [[cell]]
    if exception is None:
        assert protocol.parse_request(message) == [[float(cell)]]
    else:
        with pytest.raises(exception):
            protocol.parse_request(message)


# ------------------------- покрытие решений find_zero_columns/format_result
def test_find_zero_columns_decision_empty_matrix():
    assert processing_module.find_zero_columns([]) == []


def test_find_zero_columns_decision_no_zero():
    assert processing_module.find_zero_columns([[1.0], [2.0]]) == []


def test_find_zero_columns_decision_with_zero():
    assert processing_module.find_zero_columns([[1.0], [0.0]]) == [0]


def test_find_zero_columns_skips_non_zero_column():
    assert processing_module.find_zero_columns([[0.0, 1.0]]) == [0]


# ---------------------------------------------- покрытие решений parse_row
@pytest.mark.parametrize("text, width, expected", [
    ("1 2", 2, [1.0, 2.0]),
    ("1 2 3", 2, InputDataError),
    ("1 abc", 2, InputDataError),
    ("1 nan", 2, InputDataError),
    ("1,5 2", 2, [1.5, 2.0]),
])
def test_parse_row_decision_coverage(text, width, expected):
    if expected is InputDataError:
        with pytest.raises(InputDataError):
            input_module.parse_row(text, width, 1)
    else:
        assert input_module.parse_row(text, width, 1) == expected
