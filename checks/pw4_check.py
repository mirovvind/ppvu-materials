"""Самопроверка практической работы № 4.

Запуск из корня проекта: uv run python -m checks.pw4_check
Для быстрой проверки без запуска тестов: ... -m checks.pw4_check --fast
"""

import importlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import pandas as pd

# ожидаемые результаты на учебных данных
EXPECTED_MATCHED = 92164
EXPECTED_UNMATCHED = 7836
EXPECTED_ROWS = 52
EXPECTED_PEOPLE = 15
EXPECTED_TOTAL = 626500

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


def check_config() -> tuple[Any, Any, Any]:
    config = Path("config/criteria.toml")
    names = ("load_criteria", "load_quality", "load_bonus")
    loaders = [load("src.criteria", name) for name in names]
    if None in loaders:
        return None, None, None
    try:
        criteria, quality, bonus = (f(config) for f in loaders)
    except Exception as error:  # noqa: BLE001 — сообщаем о любой ошибке
        report(False, f"Настройки: config/criteria.toml не загружен: {error}")
        return None, None, None
    report(quality.min_share == 0.9, "Настройки: порог доли 0.9")
    report(
        (bonus.department, bonus.level_1, bonus.level_2)
        == ("АСУБП", 60000, 30000),
        "Настройки: кафедра АСУБП, У1 — 60000, У2 — 30000 руб.",
    )
    report(
        (bonus.person_cap, bonus.fund) == (100000, 600000),
        "Настройки: предел 100000 руб., фонд 600000 руб.",
    )
    return criteria, quality, bonus


def check_normalize() -> None:
    normalize = load("src.tables", "normalize_issn_column")
    if normalize is None:
        return
    values = pd.Series(
        ["0040-6090", "0012-365x", " 0040‑6090 ", "1811-90266", None],
        dtype="str",
    )
    got = normalize(values).tolist()
    ok = got[:3] == ["00406090", "0012365X", "00406090"]
    ok = ok and pd.isna(got[3]) and pd.isna(got[4])
    report(ok, "ISSN: нормализация столбца")


def check_merge() -> Any:
    names = ("normalize_issn_column", "read_registry", "merge_registry")
    normalize, read_registry, merge = (load("src.tables", n) for n in names)
    keys = load("src.tables", "issn_keys")
    if None in (normalize, read_registry, merge, keys):
        return None
    table = pd.DataFrame(
        {
            "journal_id": ["J1", "J2"],
            "issn_print": ["00406090", "00406090"],
            "issn_online": [None, None],
            "level": [1, 2],
        }
    )
    try:
        keys(table)
        report(False, "Таблица соответствия: повтор ISSN не обнаружен")
    except ValueError:
        report(True, "Таблица соответствия: повтор ISSN — ValueError")
    pub = pd.read_parquet("data/raw/publications.parquet")
    pub["issn"] = normalize(pub["issn"])
    registry = read_registry(Path("data/reference/journals.csv"))
    matched, unmatched = merge(pub, registry)
    report(
        len(matched) == EXPECTED_MATCHED,
        f"Сведение: сопоставлено {len(matched)}",
    )
    report(
        len(unmatched) == EXPECTED_UNMATCHED,
        f"Сведение: без пары {len(unmatched)}",
    )
    report("level" in matched.columns, "Сведение: добавлен уровень издания")
    return matched


def check_quality(matched: Any) -> None:
    check_share = load("src.tables", "check_share")
    schema = load("src.tables", "MatchedPublications")
    if check_share is None or schema is None:
        return
    try:
        check_share(85, 100, 0.9)
        report(False, "Доля: 85 из 100 при пороге 0.9 не отклонена")
    except ValueError:
        report(True, "Доля: 85 из 100 при пороге 0.9 — ValueError")
    if matched is None:
        return
    import pandera.pandas as pa

    try:
        schema.validate(matched, lazy=True)
        report(True, "Схема: сведённая таблица проходит проверку")
    except pa.errors.SchemaErrors:
        report(False, "Схема: сведённая таблица не проходит проверку")
    bad = pd.concat([matched.head(2), matched.head(1)], ignore_index=True)
    bad.loc[1, "level"] = 5
    try:
        schema.validate(bad, lazy=True)
        report(False, "Схема: повтор DOI и уровень 5 не обнаружены")
    except pa.errors.SchemaErrors as error:
        columns = set(error.failure_cases["column"])
        report(
            {"doi", "level"} <= columns,
            "Схема: обнаружены повтор DOI и уровень 5",
        )


def check_bonus(matched: Any, criteria: Any, bonus: Any) -> None:
    table = load("src.bonus", "bonus_table")
    orcid = load("src.bonus", "normalize_orcid_column")
    if table is None or orcid is None:
        return
    values = pd.Series(
        ["https://orcid.org/0000-0002-1694-233x", "0000-0002-1694-233"],
        dtype="str",
    )
    got = orcid(values).tolist()
    report(
        got[0] == "000000021694233X" and pd.isna(got[1]),
        "ORCID: нормализация столбца",
    )
    if matched is None or criteria is None or bonus is None:
        return
    authorships = pd.read_parquet("data/raw/authorships.parquet")
    staff = pd.read_csv("data/reference/staff.csv", dtype=str)
    rows = table(matched, authorships, staff, criteria, bonus)
    report(
        len(rows) == EXPECTED_ROWS,
        f"Премирование: строк «публикация — сотрудник» {len(rows)}",
    )
    report(
        rows["staff_id"].nunique() == EXPECTED_PEOPLE,
        f"Премирование: сотрудников {rows['staff_id'].nunique()}",
    )
    report(
        rows["amount"].sum() == EXPECTED_TOTAL,
        f"Премирование: сумма {rows['amount'].sum()} руб.",
    )


TABLES_HEAD = """
import pandas as _pd


"""
BONUS_HEAD = """
import pandas as _pd


"""
OK_ISSN_END = (
    "    valid = chars.str.fullmatch(r'[0-9]{7}[0-9X]')\n"
    "    return chars.where(valid)\n"
)
KEYS_END = (
    "    keys = keys.dropna(subset=['issn'])[['issn', 'journal_id']]\n"
    "    if keys['issn'].duplicated().any():\n"
    "        raise ValueError('один ISSN относится к разным изданиям')\n"
    "    return keys\n"
)
MERGE = """
def merge_registry(publications, registry):
    merged = publications.merge(
        issn_keys(registry), on='issn', how='{how}',
        validate='many_to_one', indicator=True,
    )
    found = merged['_merge'] == 'both'
    matched = merged[found].drop(columns='_merge')
    unmatched = merged[~found].drop(columns=['_merge', 'journal_id'])
    matched = matched.merge(
        journal_levels(registry), on='journal_id', validate='many_to_one'
    )
    return matched, unmatched.reset_index(drop=True)
"""
ACCEPTED = """
def accepted_publications(matched, criteria, bonus):
    year = matched['year']
    in_period = {period}
    accepted = matched[in_period{level}]
    amounts = {{1: bonus.level_1, 2: bonus.level_2}}
    return accepted.assign(pub_amount=accepted['level'].map(amounts))
"""
LEVEL_OK = " & (matched['level'] <= criteria.max_level)"
STAFF = """
def department_staff(staff, department):
    people = staff{select}.copy()
    people['orcid'] = normalize_orcid_column(people['orcid'])
    people = people.dropna(subset=['orcid'])
    {check}
    return people[['orcid', 'staff_id', 'full_name']]
"""
STAFF_OK = (
    "if people['orcid'].duplicated().any():\n"
    "        raise ValueError('один ORCID у разных сотрудников кафедры')"
)
DEFECTS = [
    (
        "src/tables.py",
        "ISSN: буквы не переводятся в верхний регистр",
        TABLES_HEAD
        + "def normalize_issn_column(issn):\n"
        + "    chars = issn.str.replace(r'[^0-9A-Z]', '', regex=True)\n"
        + OK_ISSN_END,
    ),
    (
        "src/tables.py",
        "ISSN: удаляется только обычный дефис",
        TABLES_HEAD
        + "def normalize_issn_column(issn):\n"
        + "    chars = issn.str.upper().str.replace('-', '').str.strip()\n"
        + OK_ISSN_END,
    ),
    (
        "src/tables.py",
        "Таблица соответствия: только печатный ISSN",
        TABLES_HEAD
        + "def issn_keys(registry):\n"
        + "    journals = registry.drop_duplicates('journal_id')\n"
        + "    keys = journals.rename(columns={'issn_print': 'issn'})\n"
        + KEYS_END,
    ),
    (
        "src/tables.py",
        "Таблица соответствия: строки изданий не объединяются",
        TABLES_HEAD
        + "def issn_keys(registry):\n"
        + "    keys = registry.melt(id_vars='journal_id',\n"
        + "        value_vars=['issn_print', 'issn_online'],\n"
        + "        value_name='issn')\n"
        + KEYS_END,
    ),
    (
        "src/tables.py",
        "Сведение: внутреннее соединение вместо левого внешнего",
        MERGE.format(how="inner"),
    ),
    (
        "src/tables.py",
        "Доля: порог не проверяется",
        "\ndef check_share(n_matched, total, limit):\n"
        + "    return n_matched / total\n",
    ),
    (
        "src/bonus.py",
        "ORCID: буквы не переводятся в верхний регистр",
        BONUS_HEAD
        + "def normalize_orcid_column(orcid):\n"
        + "    chars = orcid.str.replace(r'[^0-9X]', '', regex=True)\n"
        + "    return chars.where(chars.str.fullmatch(r'[0-9]{15}[0-9X]'))\n",
    ),
    (
        "src/bonus.py",
        "Премирование: начало периода не включается",
        ACCEPTED.format(
            period="(year > criteria.year_from) & (year <= criteria.year_to)",
            level=LEVEL_OK,
        ),
    ),
    (
        "src/bonus.py",
        "Премирование: уровень не проверяется",
        ACCEPTED.format(
            period="year.between(criteria.year_from, criteria.year_to)",
            level="",
        ),
    ),
    (
        "src/bonus.py",
        "Премирование: не отбирается кафедра",
        STAFF.format(select="", check="pass"),
    ),
    (
        "src/bonus.py",
        "Премирование: повтор ORCID не обнаруживается",
        STAFF.format(
            select="[staff['department'] == department]", check="pass"
        ),
    ),
    (
        "src/bonus.py",
        "Премирование: делится только между авторами с ORCID",
        BONUS_HEAD
        + "_bonus_table_ok = bonus_table\n\n\n"
        + "def bonus_table(matched, authorships, staff, criteria, bonus):\n"
        + "    known = authorships.dropna(subset=['orcid'])\n"
        + "    return _bonus_table_ok(matched, known, staff,\n"
        + "                           criteria, bonus)\n",
    ),
    (
        "src/bonus.py",
        "Премирование: сумма округляется, а не отбрасывается дробная часть",
        BONUS_HEAD
        + "_bonus_table_ok = bonus_table\n\n\n"
        + "def bonus_table(matched, authorships, staff, criteria, bonus):\n"
        + "    rows = _bonus_table_ok(matched, authorships, staff,\n"
        + "                           criteria, bonus)\n"
        + "    amounts = {1: bonus.level_1, 2: bonus.level_2}\n"
        + "    total = rows['level'].map(amounts)\n"
        + "    rows['amount'] = (total / rows['n_authors']).round()\n"
        + "    return rows\n",
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


def guarded(check: Any, *args: Any) -> Any:
    """Выполняет проверку; нереализованная функция — не пройдена."""
    try:
        return check(*args)
    except NotImplementedError as error:
        where = error.__traceback__
        while where is not None and where.tb_next is not None:
            where = where.tb_next
        name = where.tb_frame.f_code.co_name if where else "?"
        report(False, f"Функция {name} ещё не реализована")
    except Exception as error:  # noqa: BLE001 — сообщаем о любой ошибке
        report(False, f"{type(error).__name__}: {error}")
    return None


def main() -> None:
    criteria, _, bonus = check_config()
    guarded(check_normalize)
    matched = guarded(check_merge)
    guarded(check_quality, matched)
    guarded(check_bonus, matched, criteria, bonus)
    if "--fast" not in sys.argv:
        with tempfile.TemporaryDirectory() as name:
            check_tests(Path(name))
    print(f"Выполнено проверок: {sum(results)} из {len(results)}")


if __name__ == "__main__":
    main()
