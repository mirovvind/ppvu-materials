"""Самопроверка практической работы № 3.

Запуск из корня проекта: uv run python -m checks.pw3_check
Для быстрой проверки без запуска тестов: ... -m checks.pw3_check --fast
"""

import importlib
import shutil
import subprocess
import sys
import tempfile
from datetime import date
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
        results.append(False)
        return None


HEAD = (
    '[criteria]\nbasis = "Положение, п. 3.2"\n'
    'registry_version = "учебный справочник"\n'
)
BAD_CONFIGS = {
    "начало периода позже конца": "year_from = 2026\nyear_to = 2025\n"
    "max_level = 2\n",
    "уровень 5": "year_from = 2025\nyear_to = 2025\nmax_level = 5\n",
    "логическое значение вместо года": "year_from = true\n"
    "year_to = 2025\nmax_level = 2\n",
    "дробное число вместо уровня": "year_from = 2025\nyear_to = 2025\n"
    "max_level = 2.0\n",
}


def check_criteria(tmp: Path) -> Any:
    load_criteria = load("src.criteria", "load_criteria")
    if load_criteria is None:
        return None
    try:
        rules = load_criteria(Path("config/criteria.toml"))
        report(True, "Критерии: файл config/criteria.toml загружен")
    except Exception as error:  # noqa: BLE001 — сообщаем о любой ошибке
        report(False, f"Критерии: config/criteria.toml не загружен: {error}")
        return None
    report(
        (rules.year_from, rules.year_to, rules.max_level) == (2025, 2025, 2),
        "Критерии: период 2025–2025, пороговый уровень У2",
    )
    blank = HEAD.replace('"Положение, п. 3.2"', '"   "')
    cases = {name: HEAD + text for name, text in BAD_CONFIGS.items()}
    cases["ссылка из пробелов"] = (
        blank + "year_from = 2025\nyear_to = 2025\nmax_level = 2\n"
    )
    for name, text in cases.items():
        path = tmp / "bad.toml"
        path.write_text(text, encoding="utf-8")
        try:
            load_criteria(path)
            report(False, f"Критерии: принята конфигурация ({name})")
        except ValueError:
            report(True, f"Критерии: отклонена конфигурация ({name})")
    return rules


def check_decide(rules: Any) -> None:
    decide = load("src.rules", "decide")
    decision = load("src.models", "Decision")
    if decide is None or decision is None or rules is None:
        return
    cases = [
        (2025, 2, decision.ACCEPTED),
        (2025, 3, decision.REJECTED),
        (2024, None, decision.REJECTED),
        (2025, None, decision.MANUAL),
    ]
    for year, level, expected in cases:
        got = decide(year, level, rules)
        report(got == expected, f"decide({year}, {level}): {got}")


def check_registry(tmp: Path) -> None:
    rows = load("src.loaders", "load_registry_rows")
    if rows is None:
        return
    try:
        rows(tmp / "missing.csv")
        report(False, "Справочник: отсутствие файла не вызвало исключения")
    except FileNotFoundError:
        report(True, "Справочник: отсутствие файла — FileNotFoundError")
    empty = tmp / "empty.csv"
    empty.write_text("title,issn_print,issn_online,level\n", "utf-8")
    try:
        rows(empty)
        report(False, "Справочник: пустой файл не вызвал исключения")
    except ValueError:
        report(True, "Справочник: пустой файл — ValueError")


def check_pipeline(rules: Any) -> None:
    paths = load("src.pipeline", "Paths")
    run_check = load("src.pipeline", "run_check")
    if paths is None or run_check is None or rules is None:
        return
    source = paths(
        publications=Path("data/raw/crossref_sample.json"),
        registry=Path("data/reference/registry.csv"),
    )
    memo = run_check(source, rules, date(2026, 10, 1)).memo
    for line in (
        "Засчитано: 0",
        "Не засчитано: 5",
        "Направлено на ручную проверку: 18",
        "Не допущено в обработку: 7",
    ):
        report(line in memo, f"Служебная записка: «{line}»")


ISSN_HEAD = """
import re as _re


def normalize_issn(value):
    if not value:
        return None
"""
DECIDE_HEAD = """
from src.models import Decision as _D


def decide(year, level, rules):
"""
DOI_HEAD = """
import re as _re


def normalize_doi(value):
    if not value:
        return None
"""
OK_ISSN = (
    '    return chars if _re.fullmatch("[0-9]{7}[0-9X]", chars) else None\n'
)
OK_DOI = (
    '    return doi if _re.fullmatch(r"10\\.[0-9]{4,9}/\\S+", doi) else None\n'
)
DEFECTS = [
    (
        "src/normalize.py",
        "ISSN: строчная x не заменяется заглавной X",
        ISSN_HEAD
        + "    chars = ''.join(c for c in value if c.isalnum())\n"
        + OK_ISSN,
    ),
    (
        "src/normalize.py",
        "ISSN: цифры проверяются методом isdigit",
        ISSN_HEAD
        + "    chars = ''.join(c for c in value.upper() if c.isalnum())\n"
        + "    ok = len(chars) == 8 and chars[:7].isdigit()\n"
        + "    ok = ok and (chars[7].isdigit() or chars[7] == 'X')\n"
        + "    return chars if ok else None\n",
    ),
    (
        "src/normalize.py",
        "ISSN: удаляется только дефис",
        ISSN_HEAD + "    chars = value.upper().replace('-', '')\n" + OK_ISSN,
    ),
    (
        "src/normalize.py",
        "ISSN: шаблон проверяется методом match",
        ISSN_HEAD
        + "    chars = ''.join(c for c in value.upper() if c.isalnum())\n"
        + "    return chars if _re.match('[0-9]{7}[0-9X]', chars) else None\n",
    ),
    (
        "src/rules.py",
        "decide: строгое сравнение уровня (<)",
        DECIDE_HEAD
        + "    if not rules.year_from <= year <= rules.year_to:\n"
        + "        return _D.REJECTED\n"
        + "    if level is None:\n        return _D.MANUAL\n"
        + "    if level < rules.max_level:\n        return _D.ACCEPTED\n"
        + "    return _D.REJECTED\n",
    ),
    (
        "src/rules.py",
        "decide: начало периода не включается",
        DECIDE_HEAD
        + "    if not rules.year_from < year <= rules.year_to:\n"
        + "        return _D.REJECTED\n"
        + "    if level is None:\n        return _D.MANUAL\n"
        + "    if level <= rules.max_level:\n        return _D.ACCEPTED\n"
        + "    return _D.REJECTED\n",
    ),
    (
        "src/rules.py",
        "decide: конец периода не включается",
        DECIDE_HEAD
        + "    if not rules.year_from <= year < rules.year_to + 0:\n"
        + "        return _D.REJECTED\n"
        + "    if level is None:\n        return _D.MANUAL\n"
        + "    if level <= rules.max_level:\n        return _D.ACCEPTED\n"
        + "    return _D.REJECTED\n",
    ),
    (
        "src/rules.py",
        "decide: неизвестный уровень — «не засчитана»",
        DECIDE_HEAD
        + "    if not rules.year_from <= year <= rules.year_to:\n"
        + "        return _D.REJECTED\n"
        + "    if level is None:\n        return _D.REJECTED\n"
        + "    if level <= rules.max_level:\n        return _D.ACCEPTED\n"
        + "    return _D.REJECTED\n",
    ),
    (
        "src/rules.py",
        "decide: уровень проверяется раньше периода",
        DECIDE_HEAD
        + "    if level is None:\n        return _D.MANUAL\n"
        + "    if not rules.year_from <= year <= rules.year_to:\n"
        + "        return _D.REJECTED\n"
        + "    if level <= rules.max_level:\n        return _D.ACCEPTED\n"
        + "    return _D.REJECTED\n",
    ),
    (
        "src/normalize.py",
        "DOI: регистр букв не приводится",
        DOI_HEAD
        + "    doi = value.strip()\n"
        + "    doi = doi.removeprefix('https://doi.org/')\n"
        + OK_DOI,
    ),
    (
        "src/normalize.py",
        "DOI: пробелы по краям не удаляются",
        DOI_HEAD
        + "    doi = value.lower()\n"
        + "    doi = doi.removeprefix('https://doi.org/')\n"
        + OK_DOI,
    ),
]


def run_tests(root: Path) -> bool:
    """Запускает тесты проекта; True — все тесты пройдены."""
    done = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    return done.returncode == 0


def copy_project(tmp: Path) -> Path:
    root = tmp / "project"
    shutil.copytree("src", root / "src")
    shutil.copytree("tests", root / "tests")
    shutil.copy("pyproject.toml", root)
    return root


def check_tests(tmp: Path) -> None:
    if not Path("tests").is_dir():
        report(False, "Тесты: нет каталога tests")
        return
    root = copy_project(tmp)
    if not run_tests(root):
        report(False, "Тесты: не пройдены на исходном коде (uv run pytest)")
        return
    report(True, "Тесты: пройдены на исходном коде")
    for file, name, code in DEFECTS:
        shutil.rmtree(root)
        root = copy_project(tmp)
        with (root / file).open("a", encoding="utf-8") as target:
            target.write("\n" + code)
        caught = not run_tests(root)
        report(caught, f"Дефектный вариант обнаружен тестами: {name}")


def guarded(check: Any, *args: Any) -> None:
    """Выполняет проверку; нереализованная функция — не пройдена."""
    try:
        check(*args)
    except NotImplementedError as error:
        where = error.__traceback__
        while where is not None and where.tb_next is not None:
            where = where.tb_next
        name = where.tb_frame.f_code.co_name if where else "?"
        report(False, f"Функция {name} ещё не реализована")


def main() -> None:
    with tempfile.TemporaryDirectory() as name:
        tmp = Path(name)
        rules = check_criteria(tmp)
        guarded(check_decide, rules)
        guarded(check_registry, tmp)
        guarded(check_pipeline, rules)
        if "--fast" not in sys.argv:
            check_tests(tmp)
    print(f"Выполнено проверок: {sum(results)} из {len(results)}")


if __name__ == "__main__":
    main()
