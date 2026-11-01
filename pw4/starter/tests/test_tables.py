"""Тесты сведения выгрузки со справочником изданий."""

import pandas as pd
import pytest

from src.tables import issn_keys, normalize_issn_column

# дополнить случаями из таблицы 4.4 указаний
CASES = [
    ("0040-6090", "00406090"),  # обычная запись
    (None, None),  # значение отсутствует
]


def test_normalize_issn_column() -> None:
    values = pd.Series([value for value, _ in CASES], dtype="str")
    result = normalize_issn_column(values)
    for (value, expected), got in zip(CASES, result, strict=True):
        if expected is None:
            assert pd.isna(got), value
        else:
            assert got == expected, value


def registry(*rows: tuple[str, str | None, str | None, int]) -> pd.DataFrame:
    columns = ["journal_id", "issn_print", "issn_online", "level"]
    return pd.DataFrame(list(rows), columns=columns)


def test_duplicate_issn_raises() -> None:
    table = registry(
        ("J1", "00406090", None, 1),
        ("J2", "00406090", "18792731", 2),
    )
    with pytest.raises(ValueError, match="разным изданиям"):
        issn_keys(table)


# добавить тесты merge_registry, check_share и схемы (п. 5.1 указаний)
