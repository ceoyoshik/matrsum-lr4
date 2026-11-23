"""Интеграционные тесты: взаимодействие модулей ввода, обработки и вывода."""
import os
import subprocess
import sys
import textwrap

import pytest

import matrsum
import mapping
import protocol
from errors import (InputDataError, ModuleTimeoutError,
                    ModuleUnavailableError)
from helpers import Reader, inprocess_runner

pytestmark = pytest.mark.integration

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))


def data(matrix):
    """InputData по матрице (стенд «модуль ввода -> модуль обработки»)."""
    return mapping.InputData(n=len(matrix), m=len(matrix[0]), matrix=matrix)


# ------------------------------------------------ стенд: ввод -> обработка
def test_input_to_processing_through_files(exchange_dir):
    result = matrsum.integrate(data([[1, 0, 2], [3, 4, 5]]), exchange_dir,
                               runner=inprocess_runner)
    assert result == mapping.OutputData((2,), 4.0)


def test_integrate_writes_request_and_response(exchange_dir):
    matrsum.integrate(data([[0]]), exchange_dir, runner=inprocess_runner)
    request = protocol.load_json(os.path.join(exchange_dir, "request.json"))
    response = protocol.load_json(os.path.join(exchange_dir,
                                               "response.json"))
    assert request["payload"] == {"rows": 1, "cols": 1, "matrix": [[0]]}
    assert response["payload"] == {"zero_columns": [1], "sum": 0.0}


def test_integrate_with_real_subprocess(exchange_dir):
    result = matrsum.integrate(data([[1, 0], [2, 3]]), exchange_dir)
    assert result.columns == (2,)
    assert result.total == 3.0


# ------------------------------------------------------------ устойчивость
def test_integrate_retries_after_module_failure(exchange_dir):
    calls = []

    def failing_once(request_path, response_path, timeout):
        calls.append(1)
        if len(calls) == 1:
            raise ModuleUnavailableError("сбой запуска")
        inprocess_runner(request_path, response_path, timeout)

    result = matrsum.integrate(data([[0]]), exchange_dir,
                               attempts=2, runner=failing_once)
    assert result.total == 0.0
    assert len(calls) == 2


def test_integrate_raises_after_all_attempts(exchange_dir):
    calls = []

    def always_fails(request_path, response_path, timeout):
        calls.append(1)
        raise ModuleTimeoutError("нет ответа")

    with pytest.raises(ModuleTimeoutError):
        matrsum.integrate(data([[0]]), exchange_dir,
                          attempts=3, runner=always_fails)
    assert len(calls) == 3


def test_integrate_attempts_zero_still_tries_once(exchange_dir):
    calls = []

    def runner(request_path, response_path, timeout):
        calls.append(1)
        inprocess_runner(request_path, response_path, timeout)

    matrsum.integrate(data([[0]]), exchange_dir, attempts=0, runner=runner)
    assert len(calls) == 1


def test_integrate_removes_stale_response(exchange_dir):
    stale = os.path.join(exchange_dir, "response.json")
    protocol.dump_json(stale, protocol.build_response([9], 123.0))

    def no_response(request_path, response_path, timeout):
        return None

    with pytest.raises(ModuleUnavailableError):
        matrsum.integrate(data([[0]]), exchange_dir, attempts=1,
                          runner=no_response)


def test_integrate_propagates_module_error_message(exchange_dir):
    def writes_error(request_path, response_path, timeout):
        protocol.dump_json(response_path,
                           protocol.build_error(protocol.ERR_INVALID_DATA,
                                                "плохие данные"))

    with pytest.raises(InputDataError) as error:
        matrsum.integrate(data([[0]]), exchange_dir, runner=writes_error)
    assert "плохие данные" in str(error.value)


# ------------------------------------------------ запуск внешнего процесса
def test_run_processing_subprocess_success(exchange_dir):
    request_path = os.path.join(exchange_dir, "request.json")
    response_path = os.path.join(exchange_dir, "response.json")
    protocol.dump_json(request_path, protocol.build_request(1, 1, [[0]]))
    matrsum.run_processing_subprocess(request_path, response_path, timeout=30)
    assert protocol.load_json(response_path)["type"] == protocol.MSG_RESPONSE


def test_run_processing_subprocess_timeout(exchange_dir, tmp_path):
    slow = tmp_path / "slow.py"
    slow.write_text("import time\ntime.sleep(5)\n", encoding="utf-8")
    with pytest.raises(ModuleTimeoutError):
        matrsum.run_processing_subprocess(
            "request.json", "response.json", timeout=0.2,
            script=str(slow))


def test_run_processing_subprocess_bad_exit_code(exchange_dir, tmp_path):
    broken = tmp_path / "broken.py"
    broken.write_text("import sys\nsys.exit(7)\n", encoding="utf-8")
    with pytest.raises(ModuleUnavailableError) as error:
        matrsum.run_processing_subprocess(
            "request.json", "response.json", timeout=30,
            script=str(broken))
    assert "7" in str(error.value)


def test_run_processing_subprocess_missing_interpreter(exchange_dir,
                                                       monkeypatch):
    monkeypatch.setattr(matrsum.sys, "executable", "/nonexistent/python")
    with pytest.raises(ModuleUnavailableError):
        matrsum.run_processing_subprocess(
            "request.json", "response.json", timeout=30)


# ------------------------------------------------------- точка входа main
def test_main_success_with_workdir(exchange_dir):
    output = []
    code = matrsum.main(["--workdir", exchange_dir],
                        read=Reader(["1", "2", "0 5"]),
                        write=output.append,
                        runner=inprocess_runner)
    assert code == matrsum.EXIT_SUCCESS
    assert output == ["Столбцы с нулевым элементом: 1\n"
                      "Сумма элементов этих столбцов: 0.000"]
    assert os.path.exists(os.path.join(exchange_dir, "request.json"))


def test_main_uses_temporary_workdir(capsys):
    code = matrsum.main([], read=Reader(["1", "1", "0"]),
                        runner=inprocess_runner)
    assert code == matrsum.EXIT_SUCCESS
    assert "Сумма элементов этих столбцов: 0.000" in capsys.readouterr().out


def test_main_data_error(capsys):
    code = matrsum.main([], read=Reader(["abc"]), runner=inprocess_runner)
    assert code == matrsum.EXIT_DATA_ERROR
    assert "Ошибка данных" in capsys.readouterr().err


def test_main_integration_error(capsys):
    def broken(request_path, response_path, timeout):
        raise ModuleTimeoutError("тайм-аут")

    code = matrsum.main([], read=Reader(["1", "1", "0"]), runner=broken)
    assert code == matrsum.EXIT_INTEGRATION_ERROR
    assert "Ошибка интеграции" in capsys.readouterr().err


def test_main_custom_error_writer():
    messages = []
    code = matrsum.main([], read=Reader(["0"]), write_err=messages.append)
    assert code == matrsum.EXIT_DATA_ERROR
    assert messages and messages[0].startswith("Ошибка данных")


def test_main_timeout_option_is_passed(exchange_dir):
    seen = {}

    def runner(request_path, response_path, timeout):
        seen["timeout"] = timeout
        inprocess_runner(request_path, response_path, timeout)

    matrsum.main(["--workdir", exchange_dir, "--timeout", "2.5"],
                 read=Reader(["1", "1", "0"]), runner=runner)
    assert seen["timeout"] == 2.5


def test_build_parser_defaults():
    args = matrsum.build_parser().parse_args([])
    assert args.timeout == matrsum.DEFAULT_TIMEOUT
    assert args.workdir is None


# ------------------------------------------------------ сквозной запуск CLI
def run_cli(stdin_text, *args):
    return subprocess.run(
        [sys.executable, os.path.join(ROOT_DIR, "src", "matrsum.py"), *args],
        input=stdin_text, capture_output=True, text=True, timeout=60)


def test_cli_end_to_end():
    completed = run_cli("3\n4\n1 0 2 5\n3 4 0 6\n7 8 9 1\n")
    assert completed.returncode == 0
    assert "Столбцы с нулевым элементом: 2, 3" in completed.stdout
    assert "23.000" in completed.stdout


def test_cli_end_to_end_with_workdir(tmp_path):
    workdir = tmp_path / "exchange"
    completed = run_cli("1\n1\n1\n", "--workdir", str(workdir))
    assert completed.returncode == 0
    assert (workdir / "request.json").exists()
    assert (workdir / "response.json").exists()


def test_cli_reports_bad_input():
    completed = run_cli("2\n2\n1 2\n", "--timeout", "10")
    assert completed.returncode == matrsum.EXIT_DATA_ERROR
    assert "Ошибка данных" in completed.stderr


def test_cli_processing_module_directly(tmp_path):
    request_path = tmp_path / "request.json"
    response_path = tmp_path / "response.json"
    protocol.dump_json(str(request_path),
                       protocol.build_request(1, 2, [[0, 4]]))
    completed = subprocess.run(
        [sys.executable,
         os.path.join(ROOT_DIR, "src", "processing_module.py"),
         "--request", str(request_path),
         "--response", str(response_path)],
        capture_output=True, text=True, timeout=60)
    assert completed.returncode == protocol.EXIT_OK
    assert protocol.load_json(str(response_path))["payload"]["sum"] == 0.0


def test_cli_processing_module_prints_error(tmp_path):
    request_path = tmp_path / "request.json"
    request_path.write_text(textwrap.dedent("{bad json}"), encoding="utf-8")
    completed = subprocess.run(
        [sys.executable,
         os.path.join(ROOT_DIR, "src", "processing_module.py"),
         "--request", str(request_path),
         "--response", str(tmp_path / "response.json")],
        capture_output=True, text=True, timeout=60)
    assert completed.returncode == protocol.EXIT_REPORTED_ERROR
    response = protocol.load_json(str(tmp_path / "response.json"))
    assert response["payload"]["code"] == protocol.ERR_PROTOCOL
