"""Модульные тесты проверки критериев."""

import pytest

from src.criteria import Criteria
from src.models import Decision
from src.rules import decide

RULES = Criteria(
    basis="тестовый пример",
    year_from=2025,
    year_to=2026,
    max_level=2,
    registry_version="тестовая версия",
)

# дополнить случаями из таблицы 3.3 указаний
CASES = [
    (2025, 1, Decision.ACCEPTED),  # начало периода, высший уровень
    (2025, 3, Decision.REJECTED),  # уровень ниже порогового
]


@pytest.mark.parametrize(("year", "level", "expected"), CASES)
def test_decide(year: int, level: int | None, expected: Decision) -> None:
    assert decide(year, level, RULES) == expected
