"""Модульные тесты и тесты на основе свойств для нормализации."""

import pytest

from src.normalize import normalize_doi, normalize_issn

# дополнить случаями из таблицы 3.5 указаний
ISSN_CASES = [
    ("0040-6090", "00406090"),
    (None, None),  # значение отсутствует
]


@pytest.mark.parametrize(("raw", "expected"), ISSN_CASES)
def test_normalize_issn(raw: str | None, expected: str | None) -> None:
    assert normalize_issn(raw) == expected


# дополнить случаями из таблицы 2.4 указаний к работе 2
DOI_CASES = [
    ("10.5555/pw2.0001", "10.5555/pw2.0001"),
]


@pytest.mark.parametrize(("raw", "expected"), DOI_CASES)
def test_normalize_doi(raw: str | None, expected: str | None) -> None:
    assert normalize_doi(raw) == expected


# добавить тесты на основе свойств из пункта 3.4 лекции 3
