# МатрСум-11

Консольная программа на Python: для вещественной матрицы размерности n × m
находит общую сумму элементов только тех столбцов, которые содержат хотя бы
один нулевой элемент (вариант 11).

Версия 1.1.0: программа состоит из трёх модулей (ввод, обработка, вывод),
которые обмениваются JSON-сообщениями. Версия протестирована в ЛР №4:
381 тест, покрытие 100 %, CI на GitHub Actions.

## Структура проекта

```
matrsum/
├── src/            # исходный код
│   ├── matrsum.py            # точка входа, интеграция модулей
│   ├── input_module.py       # модуль ввода
│   ├── processing_module.py  # модуль обработки
│   ├── output_module.py      # модуль вывода
│   ├── protocol.py           # JSON-протокол обмена
│   ├── mapping.py            # сопоставление данных модулей
│   └── errors.py             # исключения интеграции
├── docs/           # документация (ТЗ, архитектура, интеграция, тесты, ревью)
├── tests/          # тесты: unit, whitebox, integration, regression,
│                   #        legacy_unittest (набор ЛР №3)
├── .github/        # CI (GitHub Actions), шаблоны Issue и Pull Request
├── requirements.txt
├── README.md
└── .gitignore
```

## Требования к окружению

- Python 3.11 или новее (проверено на 3.11, 3.12 и 3.14);
- pytest, pytest-cov, flake8 (`pip install -r requirements.txt`).

## Запуск

```
python src/matrsum.py
```

Программа запросит количество строк n, столбцов m и элементы матрицы
построчно (через пробел). Затем выведет номера столбцов с нулём и сумму.

Дополнительные параметры:

```
python src/matrsum.py --workdir exchange   # сохранить request.json и response.json
python src/matrsum.py --timeout 5          # тайм-аут модуля обработки, с
```

## Интеграция модулей

Стратегия — риск-ориентированная, протокол — обмен JSON-файлами. Описание
архитектуры, формата сообщений, таблица сопоставления данных и примеры —
в [docs/integration.md](docs/integration.md); тесты — в
[docs/integration_test.md](docs/integration_test.md); сравнение стратегий —
в [docs/integration_strategies.md](docs/integration_strategies.md);
инспекция кода — в [docs/code_review_integration.md](docs/code_review_integration.md).

## Тестирование (ЛР №4)

Запуск всех тестов с отчётом о покрытии:

```
pytest -q --cov=src --cov-report=term-missing
```

Проверка стиля:

```
flake8 src tests
```

Наборы тестов и маркеры:

| Каталог | Маркер | Что проверяет |
| --- | --- | --- |
| `tests/unit` | `unit`, `whitebox` | модули по отдельности, классы эквивалентности, границы, покрытие решений и условий |
| `tests/integration` | `integration` | обмен JSON-файлами, подпроцесс, повторы, тайм-аут, CLI |
| `tests/regression` | `regression` | эталонные результаты и формат вывода |
| `tests/legacy_unittest` | — | тесты ЛР №3, сохранённые для контроля регрессий |

Результаты: 381 тест, покрытие 100 % по операторам, решениям и условиям.

Документация по тестированию:

- [docs/testing.md](docs/testing.md) — план, сценарии, протокол, покрытие;
- [docs/bug_reports.md](docs/bug_reports.md) — 4 баг-репорта;
- [docs/testing_metrics.md](docs/testing_metrics.md) — метрики;
- [docs/testing_methods.md](docs/testing_methods.md) — сравнение методов;
- [docs/code_review.md](docs/code_review.md) — инспекция кода и ревью тестов.

CI: [.github/workflows/testing.yml](.github/workflows/testing.yml) — flake8,
тесты с порогом покрытия 95 % на Python 3.11/3.12, отдельная задача
регрессионных тестов, запуск по push, pull request, тегу и по расписанию.

## Стратегия ветвления

Используется упрощённый Git Flow:

- `main` — стабильная ветка, каждая версия помечается тегом (`v0.1.0`,
  `v1.0.0`, `v1.1.0`);
- `develop` — ветка интеграции, в неё вносятся все изменения;
- `feature/*` — короткоживущие ветки под отдельные задачи (по одной на
  каждый шаг интеграции).

Изменения попадают в `main` только слиянием из `develop` после прохождения
тестов и проверки CI. Выбор обоснован тем, что проект небольшой, но требует
стабильной основной ветки и отдельного места для экспериментов; полный
Git Flow (release/hotfix) для учебного проекта избыточен, а GitHub Flow не
даёт отдельной ветки интеграции.

## Автор

Кудинов А.А., группа ИП-25-1, Липецкий государственный технический
университет, 2026.
