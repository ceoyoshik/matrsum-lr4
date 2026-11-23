"""Модульные тесты сопоставления данных (mapping)."""
import dataclasses

import pytest

import mapping
import protocol
from errors import ProtocolError

pytestmark = pytest.mark.unit


def test_input_data_is_immutable():
    data = mapping.InputData(1, 1, [[0.0]])
    with pytest.raises(dataclasses.FrozenInstanceError):
        data.n = 2


def test_input_to_request_maps_dimensions():
    data = mapping.InputData(n=2, m=3,
                             matrix=[[1.0, 0.0, 2.0], [3.0, 4.0, 5.0]])
    message = mapping.input_to_request(data)
    assert message["payload"]["rows"] == 2
    assert message["payload"]["cols"] == 3
    assert message["payload"]["matrix"] == data.matrix


def test_processing_to_response_renumbers_columns():
    message = mapping.processing_to_response([0, 2, 4], 10)
    assert message["payload"]["zero_columns"] == [1, 3, 5]


def test_processing_to_response_converts_sum_to_float():
    message = mapping.processing_to_response([], 0)
    assert isinstance(message["payload"]["sum"], float)


def test_processing_to_response_empty_columns():
    message = mapping.processing_to_response([], 0.0)
    assert message["payload"]["zero_columns"] == []


def test_response_to_output_converts_types():
    message = protocol.build_response([1, 3], 23)
    result = mapping.response_to_output(message)
    assert result.columns == (1, 3)
    assert isinstance(result.columns, tuple)
    assert result.total == 23.0


def test_response_to_output_propagates_protocol_error():
    with pytest.raises(ProtocolError):
        mapping.response_to_output({"type": "bad"})


def test_output_data_is_immutable():
    result = mapping.OutputData((1,), 1.0)
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.total = 2.0
