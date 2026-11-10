"""Тесты сопоставления по названию издания (заготовка)."""

import pytest

from src.criteria import Matching
from src.matching import AUTO, classify, normalize_title

RULES = Matching(
    auto_accept=95,
    manual_review=85,
    author_accept=100,
    author_review=95,
    abbreviations={"j": "journal", "вестн": "вестник"},
)


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Вестник прикладной информатики", "вестник прикладной информатики"),
        # остальные случаи таблицы 5.4
    ],
)
def test_normalize_title(title: str | None, expected: str) -> None:
    assert normalize_title(title, RULES.abbreviations) == expected


@pytest.mark.parametrize(
    ("score", "same", "expected"),
    [
        (100, True, AUTO),
        # остальные случаи таблицы 5.4
    ],
)
def test_classify(score: int, same: bool, expected: str) -> None:
    assert classify(score, same, RULES) == expected
