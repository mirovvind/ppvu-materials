"""Тесты служебной записки (заготовка)."""

from datetime import date
from pathlib import Path

import pandas as pd

from src.criteria import Bonus, Criteria, Memo
from src.memo import PUBLICATIONS, MemoInfo, plural

TEMPLATE = Path("templates/memo.docx")


def test_plural() -> None:
    forms = {
        1: "публикация",
        2: "публикации",
        5: "публикаций",
    }
    assert {n: plural(n, PUBLICATIONS) for n in forms} == forms


def info(review: int) -> MemoInfo:
    return MemoInfo(
        memo=Memo(
            recipient="Директору института ПИИТМ",
            sender="заведующего кафедрой АСУБП",
            signer="Заведующий кафедрой АСУБП",
        ),
        criteria=Criteria(
            basis="Положение (тест)",
            year_from=2025,
            year_to=2025,
            max_level=2,
            registry_version="тестовый справочник",
        ),
        bonus=Bonus(
            basis="Положение о премировании (тест)",
            department="АСУБП",
            level_1=60000,
            level_2=30000,
            person_cap=100000,
            fund=60000,
        ),
        run_id=7,
        registry_sha256="0123456789abcdef",
        review=review,
        today=date(2026, 11, 20),
    )


def paid() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "staff_id": ["S1", "S2"],
            "full_name": ["Иванов Иван Иванович", "Петров Пётр Петрович"],
            "accrued": [112500, 30000],
            "capped": [100000, 30000],
            "share": [0.4615, 0.4615],
            "paid": [46150, 13845],
            "publications": [2, 1],
        }
    )
