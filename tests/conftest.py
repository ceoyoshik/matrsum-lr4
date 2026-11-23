"""Общая настройка pytest: пути импорта, фикстуры и вспомогательные данные."""
import os
import sys

import pytest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(TESTS_DIR)
SRC_DIR = os.path.join(ROOT_DIR, "src")

for path in (SRC_DIR, TESTS_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)


@pytest.fixture
def exchange_dir(tmp_path):
    """Каталог для файлов обмена request.json/response.json."""
    directory = tmp_path / "exchange"
    directory.mkdir()
    return str(directory)
