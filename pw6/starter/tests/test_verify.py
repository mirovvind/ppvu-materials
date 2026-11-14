"""Тесты сверки публикаций с ответами сервиса (заготовка)."""

import pandas as pd

from src.client import FOUND, WorkResult
from src.criteria import Bonus
from src.verify import CONFIRMED, decide

BONUS = Bonus(
    basis="Положение (тест)",
    department="АСУБП",
    level_1=60000,
    level_2=30000,
    person_cap=100000,
    fund=60000,
)


def found(year: int, doi: str = "10.1/a") -> WorkResult:
    issued = {"date-parts": [[year, 3, 1]]}
    work = {"DOI": doi, "title": ["Статья"], "issued": issued}
    return WorkResult(doi, FOUND, work, 1)


def rows() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "doi": ["d1", "d2", "d3"],
            "year": [2025, 2025, 2025],
            "staff_id": ["S1", "S1", "S2"],
            "full_name": ["Иванов И. И.", "Иванов И. И.", "Петров П. П."],
            "amount": [60000, 52500, 30000],
        }
    )


def test_decide_confirmed() -> None:
    assert decide(found(2025), 2025) == (CONFIRMED, "")
