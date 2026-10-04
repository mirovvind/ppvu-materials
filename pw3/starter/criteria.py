"""Критерии проверки публикаций: описание и загрузка.

Начальный вариант без ограничений: дополняется в п. 4.2 указаний.
"""

import tomllib
from pathlib import Path

from pydantic import BaseModel


class Criteria(BaseModel):
    """Критерии из локального нормативного акта."""

    basis: str  # ссылка на локальный акт
    year_from: int  # начало отчётного периода
    year_to: int  # конец отчётного периода
    max_level: int  # пороговый уровень издания
    registry_version: str  # версия справочника изданий


def load_criteria(path: Path) -> Criteria:
    """Читает критерии из файла и проверяет их."""
    with path.open("rb") as file:
        data = tomllib.load(file)
    return Criteria.model_validate(data["criteria"])
