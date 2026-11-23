"""Модульные тесты модуля обработки (чёрный ящик + граничные значения)."""
import pytest

import processing_module
import protocol
from errors import InputDataError
from helpers import load_cases

pytestmark = pytest.mark.unit


# --------------------------------------------------------- find_zero_columns
def test_no_zero_columns():
    matrix = [[1.0, 2.0], [3.0, 4.0]]
    assert processing_module.find_zero_columns(matrix) == []


def test_zero_in_single_column():
    matrix = [[1.0, 0.0], [3.0, 4.0]]
    assert processing_module.find_zero_columns(matrix) == [1]


def test_zero_in_every_column():
    matrix = [[0.0, 0.0], [0.0, 0.0]]
    assert processing_module.find_zero_columns(matrix) == [0, 1]


def test_zero_in_last_row():
    matrix = [[1.0], [2.0], [0.0]]
    assert processing_module.find_zero_columns(matrix) == [0]


def test_several_zeros_in_one_column_counted_once():
    matrix = [[0.0, 1.0], [0.0, 2.0], [0.0, 3.0]]
    assert processing_module.find_zero_columns(matrix) == [0]


def test_negative_zero_is_zero():
    matrix = [[-0.0, 5.0]]
    assert processing_module.find_zero_columns(matrix) == [0]


def test_single_cell_zero():
    assert processing_module.find_zero_columns([[0.0]]) == [0]


def test_empty_matrix_has_no_zero_columns():
    assert processing_module.find_zero_columns([]) == []


# ---------------------------------------------------------- sum_zero_columns
def test_sum_without_zero_columns_is_zero():
    columns, total = processing_module.sum_zero_columns([[1.0, 2.0]])
    assert columns == []
    assert total == 0.0


def test_sum_single_column():
    columns, total = processing_module.sum_zero_columns([[0.0], [2.0], [3.0]])
    assert columns == [0]
    assert total == 5.0


def test_sum_two_columns():
    matrix = [[1.0, 0.0, 2.0], [0.0, 4.0, 3.0]]
    columns, total = processing_module.sum_zero_columns(matrix)
    assert columns == [0, 1]
    assert total == 1.0 + 0.0 + 0.0 + 4.0


def test_sum_counts_each_element_once():
    # Нулевой столбец: сумма всех его элементов, а не только нулей.
    matrix = [[0.0, 1.0], [0.0, 2.0]]
    _, total = processing_module.sum_zero_columns(matrix)
    assert total == 0.0


def test_sum_is_exact_for_fractions():
    # fsum() даёт 1.0, обычное sum() — 0.9999999999999999.
    matrix = [[0.1]] * 10 + [[0.0]]
    _, total = processing_module.sum_zero_columns(matrix)
    assert total == 1.0


def test_sum_large_values():
    matrix = [[0.0, 5e307], [5e307, 0.0]]
    columns, total = processing_module.sum_zero_columns(matrix)
    assert columns == [0, 1]
    assert total == 1e308


def test_ragged_matrix_raises_input_data_error():
    """Дефект BUG-2: рваная матрица должна давать InputDataError."""
    with pytest.raises(InputDataError):
        processing_module.find_zero_columns([[1.0, 2.0], [3.0]])


# ------------------------------------------------------------ handle_request
def test_handle_request_success():
    request = protocol.build_request(2, 3, [[1, 0, 2], [3, 4, 5]])
    response = processing_module.handle_request(request)
    assert response["type"] == protocol.MSG_RESPONSE
    assert response["payload"]["zero_columns"] == [2]
    assert response["payload"]["sum"] == 4.0


def test_handle_request_returns_error_message_not_exception():
    response = processing_module.handle_request({"type": "bad"})
    assert response["type"] == protocol.MSG_ERROR


def test_handle_request_version_conflict():
    request = protocol.build_request(1, 1, [[0]])
    request["version"] = "2.0"
    response = processing_module.handle_request(request)
    assert response["payload"]["code"] == protocol.ERR_VERSION


def test_handle_request_invalid_data_code():
    request = protocol.build_request(3, 2, [[1, 2], [3, 4]])
    response = processing_module.handle_request(request)
    assert response["payload"]["code"] == protocol.ERR_INVALID_DATA


def test_handle_request_protocol_error_code():
    request = protocol.build_request(1, 1, [[0]])
    request["type"] = "unknown"
    response = processing_module.handle_request(request)
    assert response["payload"]["code"] == protocol.ERR_PROTOCOL


def test_handle_request_non_object_message():
    response = processing_module.handle_request("not a message")
    assert response["payload"]["code"] == protocol.ERR_PROTOCOL


def test_handle_request_huge_integer_is_invalid_data():
    """Дефект BUG-3: огромное целое не должно ронять обработку."""
    message = {
        "version": protocol.PROTOCOL_VERSION,
        "type": protocol.MSG_REQUEST,
        "payload": {"rows": 1, "cols": 1, "matrix": [[10 ** 400]]},
    }
    response = processing_module.handle_request(message)
    assert response["type"] == protocol.MSG_ERROR
    assert response["payload"]["code"] == protocol.ERR_INVALID_DATA


def test_handle_request_cases_from_data_file():
    for case in load_cases():
        response = processing_module.handle_request(
            protocol.build_request(len(case["matrix"]),
                                   len(case["matrix"][0]),
                                   case["matrix"]))
        assert response["payload"]["zero_columns"] == case["zero_columns"], \
            case["name"]
        assert response["payload"]["sum"] == pytest.approx(case["sum"]), \
            case["name"]


# -------------------------------------------------------------- process_files
def test_process_files_writes_response(tmp_path):
    request_path = tmp_path / "request.json"
    response_path = tmp_path / "response.json"
    protocol.dump_json(str(request_path),
                       protocol.build_request(1, 2, [[0, 5]]))
    assert processing_module.process_files(str(request_path),
                                           str(response_path)) is True
    response = protocol.load_json(str(response_path))
    assert response["payload"] == {"zero_columns": [1], "sum": 0.0}


def test_process_files_returns_false_for_error_message(tmp_path):
    request_path = tmp_path / "request.json"
    response_path = tmp_path / "response.json"
    protocol.dump_json(str(request_path),
                       protocol.build_request(3, 2, [[1, 2]]))
    assert processing_module.process_files(str(request_path),
                                           str(response_path)) is False


def test_process_files_broken_json_is_reported(tmp_path):
    request_path = tmp_path / "request.json"
    response_path = tmp_path / "response.json"
    request_path.write_text("{broken", encoding="utf-8")
    assert processing_module.process_files(str(request_path),
                                           str(response_path)) is False
    response = protocol.load_json(str(response_path))
    assert response["payload"]["code"] == protocol.ERR_PROTOCOL


# ---------------------------------------------------------------------- main
def test_main_success(tmp_path):
    request_path = tmp_path / "request.json"
    response_path = tmp_path / "response.json"
    protocol.dump_json(str(request_path),
                       protocol.build_request(1, 1, [[0]]))
    code = processing_module.main(["--request", str(request_path),
                                   "--response", str(response_path)])
    assert code == protocol.EXIT_OK


def test_main_reported_error(tmp_path):
    request_path = tmp_path / "request.json"
    response_path = tmp_path / "response.json"
    protocol.dump_json(str(request_path),
                       protocol.build_request(3, 2, [[1, 2]]))
    code = processing_module.main(["--request", str(request_path),
                                   "--response", str(response_path)])
    assert code == protocol.EXIT_REPORTED_ERROR


def test_main_missing_request_file_fails(tmp_path, capsys):
    code = processing_module.main([
        "--request", str(tmp_path / "absent.json"),
        "--response", str(tmp_path / "response.json")])
    assert code == protocol.EXIT_FAILURE
    assert "Модуль обработки" in capsys.readouterr().err


def test_main_requires_arguments():
    with pytest.raises(SystemExit):
        processing_module.main([])
