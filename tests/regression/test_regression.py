"""Регрессионные тесты: фиксируют поведение, проверенное ранее.

Набор запускается в CI при каждом изменении кода (см. .github/workflows/
testing.yml, задача «regression»), чтобы исправление одного дефекта не
изменило корректные результаты других сценариев.
"""
import json

import pytest

import mapping
import matrsum
import output_module
import processing_module
import protocol
from helpers import Reader, inprocess_runner, load_cases

pytestmark = pytest.mark.regression


@pytest.mark.parametrize("case", load_cases(),
                         ids=[case["name"] for case in load_cases()])
def test_known_results_are_stable(case):
    response = processing_module.handle_request(
        protocol.build_request(len(case["matrix"]),
                               len(case["matrix"][0]),
                               case["matrix"]))
    assert response["type"] == protocol.MSG_RESPONSE
    assert response["payload"]["zero_columns"] == case["zero_columns"]
    assert response["payload"]["sum"] == pytest.approx(case["sum"])


def test_textbook_example_from_specification():
    """ТЗ: матрица 3x4, сумма столбцов с нулями — 23.000."""
    matrix = [[1, 0, 2, 5], [3, 4, 0, 6], [7, 8, 9, 1]]
    columns, total = processing_module.sum_zero_columns(matrix)
    assert columns == [1, 2]
    assert output_module.format_number(total) == "23.000"


def test_protocol_envelope_is_stable():
    message = mapping.input_to_request(
        mapping.InputData(1, 2, [[0.0, 1.0]]))
    assert message == {
        "version": "1.0",
        "type": "matrix_request",
        "payload": {"rows": 1, "cols": 2, "matrix": [[0.0, 1.0]]},
    }
    response = processing_module.handle_request(message)
    assert response == {
        "version": "1.0",
        "type": "sum_response",
        "payload": {"zero_columns": [1], "sum": 0.0},
    }


def test_full_pipeline_output_text():
    written = []
    code = matrsum.main([], read=Reader(["2", "3", "1 0 2", "3 4 5"]),
                        write=written.append, runner=inprocess_runner)
    assert code == 0
    assert written == [
        "Столбцы с нулевым элементом: 2\n"
        "Сумма элементов этих столбцов: 4.000"
    ]


def test_no_zero_columns_output_text():
    written = []
    matrsum.main([], read=Reader(["1", "2", "1 2"]),
                 write=written.append, runner=inprocess_runner)
    assert written == [
        "Столбцов с нулевым элементом нет.\nСумма элементов: 0.000"
    ]


def test_large_matrix_result():
    size = 100
    matrix = [[0.0 if (i + j) % 10 == 0 else 1.0 for j in range(size)]
              for i in range(size)]
    columns, total = processing_module.sum_zero_columns(matrix)
    expected = sum(matrix[i][j] for i in range(size) for j in columns)
    assert len(columns) == size
    assert total == expected


def test_fractional_accumulation_is_exact():
    matrix = [[0.1] for _ in range(100)] + [[0.0]]
    _, total = processing_module.sum_zero_columns(matrix)
    assert total == 10.0


def test_exchange_file_format_is_stable(exchange_dir):
    matrsum.integrate(mapping.InputData(1, 2, [[0.0, 5.0]]), exchange_dir,
                      runner=inprocess_runner)
    with open(exchange_dir + "/request.json", encoding="utf-8") as handle:
        text = handle.read()
    assert json.loads(text)["type"] == "matrix_request"
    assert "[0.0, 5.0]" in text
