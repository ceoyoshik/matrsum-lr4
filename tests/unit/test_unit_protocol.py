"""Модульные тесты протокола обмена (JSON-сообщения, версии, файлы)."""
import json

import pytest

import protocol
from errors import (InputDataError, ModuleUnavailableError, ProtocolError,
                    VersionConflictError)

pytestmark = pytest.mark.unit


# ------------------------------------------------------------- is_number
@pytest.mark.parametrize("value", [1, 1.5, -2, 0.0, 1e300])
def test_is_number_accepts_numbers(value):
    assert protocol.is_number(value) is True


@pytest.mark.parametrize("value", [
    True, False, "1", None, [], {}, float("nan"), float("inf"),
])
def test_is_number_rejects_non_numbers(value):
    assert protocol.is_number(value) is False


def test_is_number_huge_integer_is_not_a_number():
    """Дефект BUG-3: огромное целое не должно давать OverflowError."""
    assert protocol.is_number(10 ** 400) is False


# ---------------------------------------------------------------- is_int
@pytest.mark.parametrize("value, expected", [
    (1, True), (-5, True), (0, True),
    (True, False), (1.0, False), ("1", False), (None, False),
])
def test_is_int(value, expected):
    assert protocol.is_int(value) is expected


# ------------------------------------------------------------- constructors
def test_build_request_structure_and_copy():
    source = [[1, 2], [3, 4]]
    message = protocol.build_request(2, 2, source)
    assert message["version"] == protocol.PROTOCOL_VERSION
    assert message["type"] == protocol.MSG_REQUEST
    assert message["payload"] == {"rows": 2, "cols": 2,
                                  "matrix": [[1, 2], [3, 4]]}
    source[0][0] = 99
    assert message["payload"]["matrix"][0][0] == 1


def test_build_response_converts_columns_to_list():
    message = protocol.build_response((1, 3), 23)
    assert message["payload"] == {"zero_columns": [1, 3], "sum": 23}
    assert message["type"] == protocol.MSG_RESPONSE


def test_build_error_structure():
    message = protocol.build_error(protocol.ERR_PROTOCOL, "беда")
    assert message["payload"] == {"code": protocol.ERR_PROTOCOL,
                                  "message": "беда"}


# -------------------------------------------------------------- check_version
@pytest.mark.parametrize("version", ["1.0", "1.9", "1.00", "01.0"])
def test_check_version_accepts_compatible(version):
    assert protocol.check_version(version) is None


@pytest.mark.parametrize("version", [
    "2.0", "0.9", "10.0",
])
def test_check_version_rejects_other_major(version):
    with pytest.raises(VersionConflictError):
        protocol.check_version(version)


@pytest.mark.parametrize("version", [
    1, 1.0, None, "1", "1.0.0", "a.b", "", ".", "1.", ".0", "1.a",
])
def test_check_version_rejects_bad_format(version):
    with pytest.raises(ProtocolError):
        protocol.check_version(version)


# ---------------------------------------------------------- raise_from_error
@pytest.mark.parametrize("code, exception", [
    (protocol.ERR_INVALID_DATA, InputDataError),
    (protocol.ERR_VERSION, VersionConflictError),
    (protocol.ERR_PROTOCOL, ProtocolError),
    ("unknown", ProtocolError),
    (None, ProtocolError),
])
def test_raise_from_error_maps_codes(code, exception):
    payload = {"code": code, "message": "причина"}
    with pytest.raises(exception):
        protocol.raise_from_error(payload)


def test_raise_from_error_default_message():
    with pytest.raises(ProtocolError) as error:
        protocol.raise_from_error({})
    assert "причина не указана" in str(error.value)


# --------------------------------------------------------- validate_envelope
def test_validate_envelope_returns_payload():
    message = protocol.build_request(1, 1, [[0]])
    payload = protocol.validate_envelope(message, protocol.MSG_REQUEST)
    assert payload["matrix"] == [[0]]


@pytest.mark.parametrize("message", [
    None, [], "text", 42,
])
def test_validate_envelope_rejects_non_objects(message):
    with pytest.raises(ProtocolError):
        protocol.validate_envelope(message, protocol.MSG_REQUEST)


@pytest.mark.parametrize("key", ["version", "type", "payload"])
def test_validate_envelope_requires_fields(key):
    message = protocol.build_request(1, 1, [[0]])
    del message[key]
    with pytest.raises(ProtocolError) as error:
        protocol.validate_envelope(message, protocol.MSG_REQUEST)
    assert key in str(error.value)


def test_validate_envelope_checks_version():
    message = protocol.build_request(1, 1, [[0]])
    message["version"] = "2.0"
    with pytest.raises(VersionConflictError):
        protocol.validate_envelope(message, protocol.MSG_REQUEST)


def test_validate_envelope_requires_payload_object():
    message = protocol.build_request(1, 1, [[0]])
    message["payload"] = []
    with pytest.raises(ProtocolError):
        protocol.validate_envelope(message, protocol.MSG_REQUEST)


def test_validate_envelope_rejects_wrong_type():
    message = protocol.build_response([], 0)
    with pytest.raises(ProtocolError) as error:
        protocol.validate_envelope(message, protocol.MSG_REQUEST)
    assert protocol.MSG_REQUEST in str(error.value)


def test_validate_envelope_transforms_error_message():
    message = protocol.build_error(protocol.ERR_INVALID_DATA, "плохие данные")
    with pytest.raises(InputDataError):
        protocol.validate_envelope(message, protocol.MSG_REQUEST)


def test_validate_envelope_accepts_expected_error_message():
    message = protocol.build_error(protocol.ERR_PROTOCOL, "ошибка")
    payload = protocol.validate_envelope(message, protocol.MSG_ERROR)
    assert payload["code"] == protocol.ERR_PROTOCOL


# -------------------------------------------------------------- parse_request
def test_parse_request_returns_float_matrix():
    message = protocol.build_request(2, 2, [[1, 2], [3, 0]])
    matrix = protocol.parse_request(message)
    assert matrix == [[1.0, 2.0], [3.0, 0.0]]
    assert all(isinstance(value, float) for row in matrix for value in row)


@pytest.mark.parametrize("rows, cols", [
    (True, 1), (1, False), (1.0, 1), (1, "1"), (None, 1),
])
def test_parse_request_requires_integer_sizes(rows, cols):
    message = protocol.build_request(1, 1, [[0]])
    message["payload"].update(rows=rows, cols=cols)
    with pytest.raises(ProtocolError):
        protocol.parse_request(message)


def test_parse_request_requires_matrix_list():
    message = protocol.build_request(1, 1, [[0]])
    message["payload"]["matrix"] = "0"
    with pytest.raises(ProtocolError):
        protocol.parse_request(message)


@pytest.mark.parametrize("rows, cols", [(0, 1), (1, 0), (1001, 1), (1, 1001)])
def test_parse_request_dimension_boundaries(rows, cols):
    message = protocol.build_request(1, 1, [[0]])
    message["payload"].update(rows=rows, cols=cols)
    with pytest.raises(InputDataError):
        protocol.parse_request(message)


def test_parse_request_accepts_max_dimension_boundary():
    message = protocol.build_request(1000, 1, [[0]] * 1000)
    assert len(protocol.parse_request(message)) == 1000


def test_parse_request_row_count_mismatch():
    message = protocol.build_request(3, 2, [[1, 2], [3, 4]])
    with pytest.raises(InputDataError):
        protocol.parse_request(message)


def test_parse_request_row_not_list():
    message = protocol.build_request(1, 2, [[1, 2]])
    message["payload"]["matrix"] = ["1 2"]
    with pytest.raises(InputDataError):
        protocol.parse_request(message)


def test_parse_request_row_width_mismatch():
    message = protocol.build_request(1, 2, [[1]])
    with pytest.raises(InputDataError):
        protocol.parse_request(message)


@pytest.mark.parametrize("value", ["1", None, True, [1], float("nan")])
def test_parse_request_rejects_bad_cells(value):
    message = protocol.build_request(1, 1, [[0]])
    message["payload"]["matrix"] = [[value]]
    with pytest.raises(InputDataError):
        protocol.parse_request(message)


def test_parse_request_huge_integer_cell():
    """Дефект BUG-3: огромное целое в матрице — это ошибка данных."""
    message = protocol.build_request(1, 1, [[0]])
    message["payload"]["matrix"] = [[10 ** 400]]
    with pytest.raises(InputDataError):
        protocol.parse_request(message)


# ------------------------------------------------------------- parse_response
def test_parse_response_returns_columns_and_float_sum():
    columns, total = protocol.parse_response(
        protocol.build_response([1, 3], 23))
    assert columns == [1, 3]
    assert total == 23.0
    assert isinstance(total, float)


def test_parse_response_empty_columns():
    message = protocol.build_response([], 0.0)
    assert protocol.parse_response(message) == ([], 0.0)


@pytest.mark.parametrize("columns", ["1", 1, None, [1.0], [True], ["1"]])
def test_parse_response_requires_integer_columns(columns):
    message = protocol.build_response([], 1.0)
    message["payload"]["zero_columns"] = columns
    with pytest.raises(ProtocolError):
        protocol.parse_response(message)


@pytest.mark.parametrize("total", ["1", None, True, float("nan"),
                                   float("inf")])
def test_parse_response_requires_finite_sum(total):
    message = protocol.build_response([], total)
    with pytest.raises(ProtocolError):
        protocol.parse_response(message)


@pytest.mark.parametrize("columns", [[0], [-1], [1001], [1, 1], [2, 1, 2]])
def test_parse_response_rejects_invalid_column_numbers(columns):
    """Дефект BUG-1: номера столбцов в ответе не проверялись."""
    message = protocol.build_response(columns, 1.0)
    with pytest.raises(ProtocolError):
        protocol.parse_response(message)


# ------------------------------------------------------- dump_json/load_json
def test_dump_and_load_roundtrip(tmp_path):
    path = tmp_path / "message.json"
    message = protocol.build_request(2, 2, [[1.5, 0], [2, 3]])
    protocol.dump_json(str(path), message)
    assert protocol.load_json(str(path)) == message


def test_dump_json_keeps_rows_on_one_line(tmp_path):
    path = tmp_path / "request.json"
    message = protocol.build_request(2, 2, [[1, 0], [2, 3]])
    protocol.dump_json(str(path), message)
    text = path.read_text(encoding="utf-8")
    assert "[1, 0]" in text
    assert "1,\n" not in text


def test_dump_json_keeps_cyrillic(tmp_path):
    path = tmp_path / "error.json"
    protocol.dump_json(str(path), protocol.build_error("code", "ошибка"))
    assert "ошибка" in path.read_text(encoding="utf-8")


def test_dump_json_is_atomic(tmp_path):
    path = tmp_path / "message.json"
    protocol.dump_json(str(path), protocol.build_response([], 0.0))
    assert not (tmp_path / "message.json.tmp").exists()
    protocol.dump_json(str(path), protocol.build_response([1], 1.0))
    assert protocol.load_json(str(path))["payload"]["zero_columns"] == [1]


def test_dump_json_rejects_unserializable(tmp_path):
    path = tmp_path / "bad.json"
    with pytest.raises(ProtocolError):
        protocol.dump_json(str(path), {"value": {1, 2}})
    assert not path.exists()


def test_dump_json_rejects_nan(tmp_path):
    path = tmp_path / "bad.json"
    with pytest.raises(ProtocolError):
        protocol.dump_json(str(path), {"value": float("nan")})


def test_dump_json_reports_unavailable_directory(tmp_path):
    path = tmp_path / "missing" / "message.json"
    with pytest.raises(ModuleUnavailableError):
        protocol.dump_json(str(path), protocol.build_response([], 0.0))


def test_load_json_missing_file(tmp_path):
    with pytest.raises(ModuleUnavailableError):
        protocol.load_json(str(tmp_path / "absent.json"))


def test_load_json_unreadable_path(tmp_path):
    directory = tmp_path / "exchange"
    directory.mkdir()
    with pytest.raises(ModuleUnavailableError):
        protocol.load_json(str(directory))


@pytest.mark.parametrize("content, encoding", [
    ("{broken", "utf-8"),
    ("", "utf-8"),
    ("[1, 2", "utf-8"),
])
def test_load_json_broken_document(tmp_path, content, encoding):
    path = tmp_path / "broken.json"
    path.write_text(content, encoding=encoding)
    with pytest.raises(ProtocolError):
        protocol.load_json(str(path))


def test_load_json_invalid_utf8(tmp_path):
    path = tmp_path / "binary.json"
    path.write_bytes(b"\xff\xfe{\x00")
    with pytest.raises(ProtocolError):
        protocol.load_json(str(path))


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity"])
def test_load_json_rejects_json_constants(tmp_path, constant):
    path = tmp_path / "constant.json"
    path.write_text('{"value": %s}' % constant, encoding="utf-8")
    with pytest.raises(ProtocolError):
        protocol.load_json(str(path))


def test_load_json_accepts_plain_numbers(tmp_path):
    path = tmp_path / "plain.json"
    path.write_text(json.dumps({"value": 1.5}), encoding="utf-8")
    assert protocol.load_json(str(path)) == {"value": 1.5}
