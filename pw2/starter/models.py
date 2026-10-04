"""Модель данных системы проверки публикаций."""

from dataclasses import dataclass, field
from datetime import date
from enum import Enum


class Quartile(Enum):
    """Квартиль издания."""

    Q1 = 1
    Q2 = 2
    Q3 = 3
    Q4 = 4


class Decision(Enum):
    """Решение по публикации."""

    ACCEPTED = "засчитана"
    REJECTED = "не засчитана"
    MANUAL = "направлена на ручную проверку"


@dataclass
class Journal:
    """Издание из справочника ЕГПНИ."""

    title: str
    issn_print: str | None
    issn_online: str | None
    level: int | None  # None — уровень не указан
    quartiles: dict[str, Quartile] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.level is not None and not 1 <= self.level <= 4:
            raise ValueError(f"недопустимый уровень: {self.level}")


@dataclass
class Publication:
    """Публикация из выгрузки или внешнего источника."""

    # Дописать поля с указанием типов (имена полей не изменять):
    # title — название публикации, обязательное;
    # year — год выхода, целое число или None;
    # doi — DOI, строка или None;
    # journal_title — название издания, строка или None;
    # authors — список строк, по умолчанию пустой;
    # issns — список строк, по умолчанию пустой.
    # Дописать метод __post_init__: отклонять пустое название
    # и год вне диапазона от 1900 до 2100.


@dataclass(frozen=True)
class CheckResult:
    """Результат проверки публикации."""

    doi: str | None
    decision: Decision
    reason: str  # обоснование решения
    registry_version: str  # версия справочника изданий
    checked_on: date  # дата проверки
    confidence: float  # степень достоверности: от 0 до 1

    def __post_init__(self) -> None:
        if not 0 <= self.confidence <= 1:
            raise ValueError(f"недопустимая степень: {self.confidence}")
