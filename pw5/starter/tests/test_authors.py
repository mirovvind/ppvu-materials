"""Тесты сопоставления авторов со справочником сотрудников (заготовка)."""

import pandas as pd

from src.authors import author_key
from src.criteria import Matching

RULES = Matching(
    auto_accept=95, manual_review=85, author_accept=100, author_review=95
)
STAFF = pd.DataFrame(
    {
        "staff_id": ["S1", "S2", "S3"],
        "full_name": [
            "Веселов Виктор Андреевич",
            "Веселова Вера Александровна",
            "Воробьёв Юрий Петрович",
        ],
    }
)


def candidates(*rows: tuple[str, str]) -> pd.DataFrame:
    """Авторы без ORCID: строки (doi, запись автора)."""
    return pd.DataFrame(rows, columns=["doi", "author"])


def test_author_key() -> None:
    assert author_key("Веселов В. А.") == "веселов ва"
