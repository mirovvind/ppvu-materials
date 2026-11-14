"""Сверка премируемых публикаций со сведениями сервиса метаданных."""

import pandas as pd

from src.client import WorkResult
from src.criteria import Bonus

CONFIRMED = "подтверждена"
NOT_IN_SERVICE = "не найдена в сервисе"
NO_ANSWER = "сервис недоступен"
YEAR_MISMATCH = "расхождение года"


def decide(result: WorkResult, year: int) -> tuple[str, str]:
    """Решение по публикации и его причина."""
    raise NotImplementedError


def verify_rows(rows: pd.DataFrame, results: list[WorkResult]) -> pd.DataFrame:
    """Решения по публикациям: столбцы doi, decision, reason."""
    years = rows.drop_duplicates("doi").set_index("doi")["year"]
    records = [(r.doi, *decide(r, int(years[r.doi]))) for r in results]
    return pd.DataFrame(records, columns=["doi", "decision", "reason"])


def confirmed_rows(
    rows: pd.DataFrame, decisions: pd.DataFrame
) -> pd.DataFrame:
    """Строки «публикация — сотрудник» подтверждённых публикаций."""
    raise NotImplementedError


def review_rows(rows: pd.DataFrame, decisions: pd.DataFrame) -> pd.DataFrame:
    """Строки неподтверждённых публикаций — для ручной проверки."""
    review = decisions[decisions["decision"] != CONFIRMED]
    return review.merge(rows, on="doi", validate="one_to_many")


def distribute(rows: pd.DataFrame, bonus: Bonus) -> pd.DataFrame:
    """Распределение фонда (функции работы 5) и число публикаций."""
    raise NotImplementedError
