"""Тесты загрузки справочника изданий: ошибки прерывают работу."""

from pathlib import Path

import pytest

from src.loaders import load_registry_rows


def test_missing_registry(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="не найден"):
        load_registry_rows(tmp_path / "registry.csv")


# добавить тест для пустого справочника (п. 5.1 указаний)
