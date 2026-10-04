"""Самопроверка практической работы № 2.

Запуск из корня проекта: uv run python -m checks.pw2_check
"""

import csv
import importlib
from pathlib import Path
from typing import Any

results: list[bool] = []


def report(ok: bool, text: str) -> None:
    results.append(ok)
    print(("ВЕРНО   " if ok else "ОШИБКА  ") + text)


def load(module_name: str, name: str) -> Any:
    try:
        module = importlib.import_module(module_name)
        return getattr(module, name)
    except (ImportError, AttributeError) as error:
        print(f"НЕТ     {module_name}.{name}: {error}")
        return None


ISSN_CASES = [
    ("0040-6090", "00406090"),
    ("0040 6090", "00406090"),
    ("00406090", "00406090"),
    ("2587-120x", "2587120X"),
    ("1811-90266", None),
    ("2071-245", None),
    ("٠٠٤٠٦٠٩٠", None),
    ("", None),
    (None, None),
]

DOI_CASES = [
    ("10.5555/pw2.0001", "10.5555/pw2.0001"),
    ("10.5555/PW2.0002", "10.5555/pw2.0002"),
    ("https://doi.org/10.5555/pw2.0007", "10.5555/pw2.0007"),
    ("http://dx.doi.org/10.5555/ABC", "10.5555/abc"),
    ("doi:10.5555/pw2.0020", "10.5555/pw2.0020"),
    ("  10.5555/pw2.0003 ", "10.5555/pw2.0003"),
    ("5555/pw2.0001", None),
    ("10.5555", None),
    ("https://example.com/10.5555/x", None),
    ("10.5555/pw2 0001", None),
    ("", None),
    (None, None),
]


def check_function(func: Any, cases: list[Any], title: str) -> None:
    if func is None:
        return
    for value, expected in cases:
        try:
            actual = func(value)
        except NotImplementedError:
            report(False, f"{title}: функция не реализована")
            return
        except Exception as error:  # noqa: BLE001
            actual = f"исключение {type(error).__name__}"
        report(actual == expected, f"{title}({value!r}) -> {actual!r}")


def expect_error(factory: Any, text: str) -> None:
    try:
        factory()
    except (ValueError, TypeError):
        report(True, text)
    else:
        report(False, text + " (ошибка не возникла)")


def check_models() -> None:
    quartile = load("src.models", "Quartile")
    journal = load("src.models", "Journal")
    publication = load("src.models", "Publication")
    if quartile is not None:
        names = [item.name for item in quartile]
        report(names == ["Q1", "Q2", "Q3", "Q4"], "Quartile: значения Q1-Q4")
    if journal is not None:
        expect_error(
            lambda: journal("Журнал", None, None, level=7),
            "Journal: уровень 7 отклоняется",
        )
    if publication is None:
        return
    fields = getattr(publication, "__dataclass_fields__", {})
    for name in ("title", "year", "doi", "journal_title", "authors", "issns"):
        report(name in fields, f"Publication: есть поле {name}")
    if not {"title", "year", "doi", "journal_title"} <= set(fields):
        return
    expect_error(
        lambda: publication(title="", year=2025, doi=None, journal_title=None),
        "Publication: пустое название отклоняется",
    )
    expect_error(
        lambda: publication(
            title="Статья", year=1025, doi=None, journal_title=None
        ),
        "Publication: год 1025 отклоняется",
    )
    first = publication(title="А", year=None, doi=None, journal_title=None)
    second = publication(title="Б", year=None, doi=None, journal_title=None)
    first.authors.append("Смирнова Анна")
    report(
        second.authors == [],
        "Publication: у каждой публикации собственный список авторов",
    )


def check_loaders() -> None:
    load_items = load("src.loaders", "load_items")
    check_records = load("src.loaders", "check_records")
    if load_items is None or check_records is None:
        return
    path = Path("data/raw/crossref_sample.json")
    if not path.exists():
        report(False, f"нет файла {path}")
        return
    accepted, rejected = check_records(load_items(path))
    report(len(accepted) == 24, f"входной контроль: принято {len(accepted)}")
    report(len(rejected) == 6, f"входной контроль: отклонено {len(rejected)}")
    log = Path("data/output/rejected.csv")
    if log.exists():
        with log.open(encoding="utf-8", newline="") as file:
            rows = list(csv.reader(file))
        count = len(rows) - 1
        report(count in (6, 7), f"журнал отклонений: записей {count}")
    else:
        report(False, "нет журнала отклонений data/output/rejected.csv")


if __name__ == "__main__":
    check_function(load("src.normalize", "normalize_issn"), ISSN_CASES, "ISSN")
    check_function(load("src.normalize", "normalize_doi"), DOI_CASES, "DOI")
    check_models()
    check_loaders()
    print(f"\nВыполнено проверок: {sum(results)} из {len(results)}")
