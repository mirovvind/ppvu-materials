"""Тесты предварительного расчёта премирования."""

import pandas as pd

from src.bonus import bonus_table
from src.criteria import Bonus, Criteria

RULES = Criteria(
    basis="тестовый пример",
    year_from=2025,
    year_to=2026,
    max_level=2,
    registry_version="тестовая версия",
)
BONUS = Bonus(
    basis="тестовое положение",
    department="АСУБП",
    level_1=60000,
    level_2=30000,
    person_cap=100000,
    fund=600000,
)
A = "0000-0002-1825-0097"  # сотрудник кафедры
B = "0000-0001-5109-3700"  # сотрудник другой кафедры
STAFF = pd.DataFrame(
    {
        "staff_id": ["S1", "S2", "S1"],
        "full_name": ["Иванов И. И.", "Петров П. П.", "Иванов И. И."],
        "orcid": [A, B, A],
        "department": ["АСУБП", "Химии", "Информатики"],  # S1 — совместитель
    }
)


def matched(*rows: tuple[str, int, int]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["doi", "year", "level"])


def authors(*rows: tuple[str, str | None]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["doi", "orcid"])


def test_share_between_all_authors() -> None:
    # три автора, из них один сотрудник кафедры и один без ORCID
    table = bonus_table(
        matched(("p1", 2025, 1)),
        authors(("p1", A), ("p1", B), ("p1", None)),
        STAFF,
        RULES,
        BONUS,
    )
    assert table["staff_id"].tolist() == ["S1"]
    assert table["amount"].tolist() == [20000]


# добавить тесты из таблицы 4.6 указаний (п. 5.1)
