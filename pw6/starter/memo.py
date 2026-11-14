"""Служебная записка на премирование по шаблону DOCX."""

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from src.criteria import Bonus, Criteria, Memo

PUBLICATIONS = ("публикация", "публикации", "публикаций")
EMPLOYEES = ("сотрудник", "сотрудника", "сотрудников")
RUBLES = ("рубль", "рубля", "рублей")


@dataclass
class MemoInfo:
    """Сведения для записки, кроме таблицы выплат."""

    memo: Memo  # реквизиты из config/criteria.toml
    criteria: Criteria
    bonus: Bonus
    run_id: int  # номер запуска сверки
    registry_sha256: str  # контрольная сумма справочника изданий
    review: int  # число публикаций на ручной проверке
    today: date


def plural(number: int, forms: tuple[str, str, str]) -> str:
    """Форма слова для числа: 1 публикация, 2 публикации, 5 публикаций."""
    raise NotImplementedError


def format_amount(amount: int) -> str:
    """Сумма с разделением разрядов: 599940 -> «599 940»."""
    return f"{amount:,}".replace(",", " ")


def rubles(amount: int) -> str:
    """Сумма в рублях: «599 940 рублей», «1 рубль»."""
    return f"{format_amount(amount)} {plural(amount, RUBLES)}"


def period_text(criteria: Criteria) -> str:
    """Отчётный период: «2025 год» или «2024–2025 годы»."""
    if criteria.year_from == criteria.year_to:
        return f"{criteria.year_from} год"
    return f"{criteria.year_from}–{criteria.year_to} годы"


def table_rows(paid: pd.DataFrame) -> list[dict[str, Any]]:
    """Строки таблицы записки: №, ФИО, публикации, начислено, к выплате."""
    raise NotImplementedError


def memo_context(paid: pd.DataFrame, info: MemoInfo) -> dict[str, Any]:
    """Значения полей шаблона записки."""
    raise NotImplementedError


def render_memo(template: Path, context: dict[str, Any], path: Path) -> None:
    """Заполняет шаблон и сохраняет записку."""
    raise NotImplementedError


# Основной уровень: сумма прописью


def amount_words(amount: int) -> str:
    """Сумма прописью: 600000 -> «Шестьсот тысяч рублей»."""
    raise NotImplementedError
