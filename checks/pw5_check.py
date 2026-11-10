"""Самопроверка практической работы № 5.

Запуск из корня проекта: uv run python -m checks.pw5_check
Для быстрой проверки без запуска тестов: ... -m checks.pw5_check --fast
"""

import importlib
import shutil
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

CONFIG = Path("config/criteria.toml")
BASIC_WORDS = {
    "вестн": "вестник",
    "изв": "известия",
    "тр": "труды",
    "j": "journal",
    "int": "international",
}
# ожидаемые результаты на учебных данных (словарь сокращений из п. 4.1)
EXPECTED_MEMO = [
    "Засчитано: 8",
    "Не засчитано: 10",
    "Направлено на ручную проверку: 5",
    "Не допущено в обработку: 7",
]
EXPECTED_QUALITY = (1.0, 0.830)  # точность и полнота при пороге 95
EXPECTED_TITLES = (3692, 542, 3785)  # принято, на проверку, публикаций
EXPECTED_ROWS = (79, 18)  # строк «публикация — сотрудник», сотрудников
EXPECTED_FUND = (933000, 920500, 0.6518, 599976)

results: list[bool] = []


def report(ok: bool, text: str) -> None:
    results.append(ok)
    print(("ВЕРНО   " if ok else "ОШИБКА  ") + text)


def load(module_name: str, name: str) -> Any:
    """Функция модуля проекта или None, если её нет."""
    try:
        module = importlib.import_module(module_name)
        return getattr(module, name)
    except (ImportError, AttributeError) as error:
        print(f"НЕТ     {module_name}.{name}: {error}")
        return None


def missing(*items: Any) -> bool:
    return any(item is None for item in items)


def guarded(title: str, check: Any, *args: Any) -> Any:
    """Выполняет проверку; любая ошибка — проверка не пройдена."""
    try:
        return check(*args)
    except NotImplementedError as error:
        where = error.__traceback__
        while where is not None and where.tb_next is not None:
            where = where.tb_next
        name = where.tb_frame.f_code.co_name if where else "?"
        report(False, f"{title}: функция {name} ещё не реализована")
    except Exception as error:  # noqa: BLE001 — сообщаем о любой ошибке
        report(False, f"{title}: {type(error).__name__}: {error}")
    return None


def check_config() -> Any:
    load_matching = load("src.criteria", "load_matching")
    if load_matching is None:
        report(False, "Настройки: нет функции load_matching")
        report(False, "Настройки: словарь сокращений не проверен")
        return None
    try:
        rules = load_matching(CONFIG)
    except Exception as error:  # noqa: BLE001 — сообщаем о любой ошибке
        report(False, f"Настройки: раздел [matching] не загружен: {error}")
        report(False, "Настройки: словарь сокращений не проверен")
        return None
    report(
        (rules.auto_accept, rules.manual_review) == (95, 85)
        and (rules.author_accept, rules.author_review) == (100, 95),
        "Настройки: пороги 95 и 85, для авторов 100 и 95",
    )
    words = rules.abbreviations
    report(
        all(words.get(key) == value for key, value in BASIC_WORDS.items()),
        "Настройки: словарь сокращений содержит пять сокращений п. 4.1",
    )
    return rules


def check_normalize() -> None:
    normalize = load("src.matching", "normalize_title")
    if missing(normalize):
        report(False, "Нормализация названия: нет функции")
        return
    cases = [
        ("ВЕСТНИК  Науки.", {}, "вестник науки"),
        ("Учёные записки", {}, "ученые записки"),
        ("Food & Nutrition", {}, "food and nutrition"),
        ("J. of Food Sci.", {"j": "journal"}, "journal of food sci"),
        (None, {}, ""),
    ]  # fmt: skip
    got = [normalize(title, words) for title, words, _ in cases]
    report(
        got == [expected for *_, expected in cases],
        "Нормализация названия: регистр, ё, знаки, &, сокращения, None",
    )


def check_numbers() -> None:
    numbers = load("src.matching", "numbers")
    if missing(numbers):
        report(False, "Числа в названии: нет функции")
        return
    ok = numbers("вестник серия 2 экономика") == ["2"]
    ok = ok and numbers("journal of food science") == []
    report(ok, "Числа в названии: номер серии")


def check_classify(rules: Any) -> None:
    classify = load("src.matching", "classify")
    names = [load("src.matching", n) for n in ("AUTO", "REVIEW", "NOT_FOUND")]
    if missing(classify, rules, *names):
        report(False, "Решение по сходству: нет функции или настроек")
        return
    auto, review, not_found = names
    cases = [
        (95, True, auto),
        (94, True, review),
        (85, True, review),
        (84, True, not_found),
        (99, False, not_found),
    ]
    got = [classify(score, same, rules) for score, same, _ in cases]
    report(
        got == [expected for *_, expected in cases],
        "Решение по сходству: границы порогов и проверка чисел",
    )


def check_pipeline(rules: Any) -> None:
    load_criteria = load("src.criteria", "load_criteria")
    run_check = load("src.pipeline", "run_check")
    paths_class = load("src.pipeline", "Paths")
    if missing(load_criteria, run_check, paths_class, rules):
        report(False, "Конвейер main.py: нет функций или настроек")
        return
    paths = paths_class(
        publications=Path("data/raw/crossref_sample.json"),
        registry=Path("data/reference/registry.csv"),
    )
    result = run_check(paths, load_criteria(CONFIG), date(2026, 11, 10), rules)
    report(
        all(line in result.memo for line in EXPECTED_MEMO),
        "Конвейер main.py: " + ", ".join(EXPECTED_MEMO),
    )


def check_assign() -> None:
    assign = load("src.matching", "assign")
    if missing(assign):
        report(False, "Задача о назначениях: нет функции assign")
        return
    scores = np.array([[85.1, 90.0], [76.7, 88.6]])
    report(
        list(assign(scores)) == [(0, 0), (1, 1)],
        "Задача о назначениях: пары с наибольшей суммой",
    )


def journals() -> pd.DataFrame:
    read_registry = load("src.tables", "read_registry")
    registry = read_registry(Path("data/reference/journals.csv"))
    return registry.drop_duplicates("journal_id").reset_index(drop=True)


def check_quality(rules: Any) -> None:
    match_titles = load("src.matching", "match_titles")
    quality = load("src.matching", "quality")
    if missing(match_titles, quality, rules):
        report(False, "Разметка: нет функций match_titles или quality")
        return
    labels = pd.read_csv("data/raw/labels.csv", dtype=str)
    found = match_titles(labels["container_title"].tolist(), journals(), rules)
    precision, recall = quality(found, labels, 95)
    if rules.abbreviations != BASIC_WORDS:
        report(precision >= 0.99, f"Разметка: точность {precision:.3f}")
        return
    report(
        (round(precision, 3), round(recall, 3)) == EXPECTED_QUALITY,
        f"Разметка, порог 95: точность {precision:.3f}, полнота {recall:.3f}",
    )


def check_authors(rules: Any) -> None:
    author_key = load("src.authors", "author_key")
    match_authors = load("src.authors", "match_authors")
    if missing(author_key, match_authors, rules):
        report(False, "Авторы: нет функций author_key или match_authors")
        return
    ok = author_key("Воробьёв  Ю.П.") == "воробьев юп"
    staff = pd.DataFrame(
        {
            "staff_id": ["S1", "S2"],
            "full_name": [
                "Веселов Виктор Андреевич",
                "Веселова Вера Александровна",
            ],
        }
    )
    authors = ["Veselova V.A.", "Петров П. П.", "Веселов В. А."]
    candidates = pd.DataFrame({"doi": ["d1", "d1", "d2"], "author": authors})
    by_orcid = pd.DataFrame({"doi": ["d2"], "staff_id": ["S1"]})
    found = match_authors(candidates, by_orcid, staff, rules)
    pairs = sorted(zip(found["doi"], found["staff_id"], found["status"]))
    ok = ok and pairs == [("d1", "S2", "принято"), ("d2", "S2", "на проверку")]
    report(ok, "Авторы: запись автора, пары внутри публикации, пороги")


def check_fund() -> None:
    best_share = load("src.fund", "best_share")
    payments = load("src.fund", "payments")
    if missing(best_share, payments):
        report(False, "Фонд: нет функций best_share или payments")
        return
    share = best_share(np.array([50000, 50000]), 60000)
    ok = abs(share - 0.6) < 1e-6
    ok = ok and abs(best_share(np.array([20000, 30000]), 60000) - 1) < 1e-6
    totals = pd.DataFrame({"capped": [33333, 50000]})
    paid = payments(totals, 0.33333, 60000)
    ok = ok and paid["paid"].tolist() == [11109, 16665]
    report(ok, "Фонд: наибольшая доля и выплаты с отбрасыванием дробной части")


def allocation(rules: Any) -> tuple[Any, ...]:
    """Повторяет расчёт программы allocate.py по функциям проекта."""
    names = {
        "src.matching": ("match_titles", "AUTO", "REVIEW"),
        "src.authors": ("match_authors", "name_rows"),
        "src.bonus": ("bonus_table", "accepted_publications"),
        "src.fund": ("person_totals", "best_share", "payments"),
    }
    f = {n: load(m, n) for m, group in names.items() for n in group}
    f["normalize_orcid_column"] = load("src.bonus", "normalize_orcid_column")
    criteria = load("src.criteria", "load_criteria")(CONFIG)
    bonus = load("src.criteria", "load_bonus")(CONFIG)
    output = Path("data/output")
    matched = pd.read_parquet(output / "matched.parquet")
    unmatched = pd.read_parquet(output / "unmatched.parquet").merge(
        pd.read_parquet("data/raw/containers.parquet"), on="doi"
    )
    titles = unmatched["container_title"].dropna().unique().tolist()
    table = journals()
    found = f["match_titles"](titles, table, rules)
    counts = [(found["status"] == f[s]).sum() for s in ("AUTO", "REVIEW")]
    auto = found[found["status"] == f["AUTO"]][
        ["container_title", "journal_id"]
    ]
    pairs = unmatched.merge(auto, on="container_title").merge(
        table[["journal_id", "level"]], on="journal_id"
    )
    full = pd.concat([matched, pairs[matched.columns]], ignore_index=True)
    authorships = pd.read_parquet("data/raw/authorships.parquet")
    staff = pd.read_csv("data/reference/staff.csv", dtype=str)
    by_orcid = f["bonus_table"](full, authorships, staff, criteria, bonus)
    accepted = f["accepted_publications"](full, criteria, bonus)
    authors = authorships[authorships["doi"].isin(accepted["doi"])]
    no_orcid = authors[f["normalize_orcid_column"](authors["orcid"]).isna()]
    people = staff[staff["department"] == bonus.department]
    by_name = f["match_authors"](no_orcid, by_orcid, people, rules)
    names_ok = by_name[by_name["status"] == f["AUTO"]]
    rows = pd.concat(
        [by_orcid, f["name_rows"](accepted, authorships, names_ok)],
        ignore_index=True,
    )
    totals = f["person_totals"](rows, bonus.person_cap)
    share = f["best_share"](totals["capped"].to_numpy(), bonus.fund)
    paid = f["payments"](totals, share, bonus.fund)
    return (*counts, len(pairs)), rows, totals, paid, bonus


def check_allocation(rules: Any, ready: bool) -> None:
    title = "Полный расчёт"
    if not ready or rules is None:
        for part in ("сопоставление по названию", "строки", "распределение"):
            report(False, f"{title}: {part} — сначала пройдите проверки выше")
        return
    if not Path("data/output/unmatched.parquet").exists():
        for part in ("сопоставление по названию", "строки", "распределение"):
            report(False, f"{title}: {part} — запустите prepare.py")
        return
    try:
        counts, rows, totals, paid, bonus = allocation(rules)
    except Exception as error:  # noqa: BLE001 — сообщаем о любой ошибке
        for part in ("сопоставление по названию", "строки", "распределение"):
            report(False, f"{title}: {part} — {type(error).__name__}: {error}")
        return
    basic = rules.abbreviations == BASIC_WORDS
    report(
        not basic or tuple(counts) == EXPECTED_TITLES,
        f"{title}: названий принято {counts[0]}, на проверку {counts[1]}, "
        f"публикаций {counts[2]}",
    )
    report(
        not basic or (len(rows), len(totals)) == EXPECTED_ROWS,
        f"{title}: строк {len(rows)}, сотрудников {len(totals)}",
    )
    got = (
        int(totals["accrued"].sum()),
        int(totals["capped"].sum()),
        round(float(paid["share"].iloc[0]), 4),
        int(paid["paid"].sum()),
    )
    ok = got == EXPECTED_FUND if basic else True
    ok = ok and got[3] <= bonus.fund and (paid["paid"] <= paid["capped"]).all()
    report(
        ok,
        f"{title}: начислено {got[0]}, с пределом {got[1]}, доля {got[2]}, "
        f"выплачивается {got[3]} руб.",
    )


MATCHING_HEAD = "\nimport re as _re\n\n\n"
AUTHORS_HEAD = "\nimport pandas as _pd\n\n\n"
CLASSIFY = """
def classify(score, same_numbers, rules):
    if {numbers}score < rules.manual_review:
        return NOT_FOUND
    if score {op} rules.auto_accept:
        return AUTO
    return {middle}
"""
NORMALIZE = """
def normalize_title(title, abbreviations):
    if title is None:
        return ''
    text = title{lower}.replace('ё', '{yo}'){amp}
    text = _re.sub(r'{pattern}', ' ', text)
    words = [{word} for word in text.split()]
    return ' '.join(word for word in words if word)
"""
OK_NORMALIZE = {
    "lower": ".lower()",
    "yo": "е",
    "amp": ".replace('&', ' and ')",
    "pattern": "[^\\w\\s]",
    "word": "abbreviations.get(word, word)",
}
MATCH_AUTHORS = """
_match_authors_ok = match_authors


def match_authors(candidates, found, staff, rules):
    {body}
"""


def normalize_defect(**changes: str) -> str:
    return MATCHING_HEAD + NORMALIZE.format(**(OK_NORMALIZE | changes))


DEFECTS = [
    (
        "src/matching.py",
        "Нормализация: регистр не приводится",
        normalize_defect(lower=""),
    ),
    (
        "src/matching.py",
        "Нормализация: буква ё не заменяется",
        normalize_defect(yo="ё"),
    ),
    (
        "src/matching.py",
        "Нормализация: знаки препинания не удаляются",
        normalize_defect(pattern="[\\t]"),
    ),
    (
        "src/matching.py",
        "Нормализация: знак & не заменяется",
        normalize_defect(amp=""),
    ),
    (
        "src/matching.py",
        "Нормализация: сокращения не раскрываются",
        normalize_defect(word="word"),
    ),
    (
        "src/matching.py",
        "Решение: числа в названии не сравниваются",
        CLASSIFY.format(numbers="", op=">=", middle="REVIEW"),
    ),
    (
        "src/matching.py",
        "Решение: порог принятия не включается",
        CLASSIFY.format(
            numbers="not same_numbers or ", op=">", middle="REVIEW"
        ),
    ),
    (
        "src/matching.py",
        "Решение: нет зоны ручной проверки",
        CLASSIFY.format(
            numbers="not same_numbers or ", op=">=", middle="NOT_FOUND"
        ),
    ),
    (
        "src/matching.py",
        "Конвейер: ISSN не используется",
        (
            "\ndef by_issn(publication, registry):\n"
            "    return publication, None, 0.0\n"
        ),
    ),
    (
        "src/matching.py",
        "Разметка: полнота делится на число принятых",
        (
            "\n_quality_ok = quality\n\n\n"
            "def quality(found, labels, threshold):\n"
            "    precision, _ = _quality_ok(found, labels, threshold)\n"
            "    return precision, precision\n"
        ),
    ),
    (
        "src/authors.py",
        "Авторы: инициалы не объединяются",
        AUTHORS_HEAD
        + (
            "_author_key_ok = author_key\n\n\n"
            "def author_key(author):\n"
            "    surname, rest = _author_key_ok(author).split(' ', 1)\n"
            "    return surname + ' ' + ' '.join(rest)\n"
        ),
    ),
    (
        "src/authors.py",
        "Авторы: латинская запись без транслитерации",
        "\ndef translit(text):\n    return text.lower()\n",
    ),
    (
        "src/authors.py",
        "Авторы: найденные по ORCID не исключаются",
        MATCH_AUTHORS.format(
            body="empty = found.iloc[0:0]\n"
            "    return _match_authors_ok(candidates, empty, staff, rules)"
        ),
    ),
    (
        "src/authors.py",
        "Авторы: порог проверки не применяется",
        MATCH_AUTHORS.format(
            body="low = rules.model_copy(update={'author_review': 0})\n"
            "    return _match_authors_ok(candidates, found, staff, low)"
        ),
    ),
    (
        "src/authors.py",
        "Авторы: сумма делится только между найденными авторами",
        (
            "\n_name_rows_ok = name_rows\n\n\n"
            "def name_rows(accepted, authorships, names):\n"
            "    known = authorships[authorships['doi'].isin(names['doi'])]\n"
            "    known = known.head(len(names))\n"
            "    return _name_rows_ok(accepted, known, names)\n"
        ),
    ),
    (
        "src/fund.py",
        "Фонд: предел на сотрудника не применяется",
        (
            "\n_person_totals_ok = person_totals\n\n\n"
            "def person_totals(rows, cap):\n"
            "    return _person_totals_ok(rows, 10**12)\n"
        ),
    ),
    (
        "src/fund.py",
        "Фонд: ограничение фонда не учитывается",
        (
            "\n_best_share_ok = best_share\n\n\n"
            "def best_share(capped, fund):\n"
            "    return _best_share_ok(capped, 10**12)\n"
        ),
    ),
    (
        "src/fund.py",
        "Фонд: выплата округляется, а не отбрасывается дробная часть",
        (
            "\n_payments_ok = payments\n\n\n"
            "def payments(totals, share, fund):\n"
            "    paid = _payments_ok(totals, share, fund)\n"
            "    paid['paid'] = (paid['capped'] * paid['share']).round()\n"
            "    return paid\n"
        ),
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


def main() -> None:
    rules = guarded("Настройки", check_config)
    before = len(results)
    guarded("Нормализация названия", check_normalize)
    guarded("Числа в названии", check_numbers)
    guarded("Решение по сходству", check_classify, rules)
    guarded("Конвейер main.py", check_pipeline, rules)
    guarded("Задача о назначениях", check_assign)
    guarded("Разметка", check_quality, rules)
    guarded("Авторы", check_authors, rules)
    guarded("Фонд", check_fund)
    ready = all(results[before:])
    check_allocation(rules, ready)
    if "--fast" not in sys.argv:
        with tempfile.TemporaryDirectory() as name:
            check_tests(Path(name))
    print(f"Выполнено проверок: {sum(results)} из {len(results)}")


if __name__ == "__main__":
    main()
