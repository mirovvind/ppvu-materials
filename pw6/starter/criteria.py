"""Критерии проверки публикаций: описание и загрузка."""

import tomllib
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Criteria(BaseModel):
    """Критерии из локального нормативного акта."""

    model_config = ConfigDict(strict=True, str_strip_whitespace=True)
    basis: str = Field(min_length=1)  # ссылка на локальный акт
    year_from: int  # начало отчётного периода
    year_to: int  # конец отчётного периода
    max_level: int = Field(ge=1, le=4)  # уровень не ниже заданного
    registry_version: str = Field(min_length=1)  # версия справочника

    @model_validator(mode="after")
    def check_period(self) -> "Criteria":
        if self.year_from > self.year_to:
            raise ValueError("начало периода позже его конца")
        return self


class Quality(BaseModel):
    """Требования к качеству сведённой таблицы."""

    model_config = ConfigDict(strict=True)
    min_share: float = Field(gt=0, le=1)  # доля сопоставленных публикаций


class Bonus(BaseModel):
    """Условия премирования (учебный пример)."""

    model_config = ConfigDict(strict=True, str_strip_whitespace=True)
    basis: str = Field(min_length=1)  # ссылка на положение о премировании
    department: str = Field(min_length=1)  # премируемая кафедра
    level_1: int = Field(gt=0)  # сумма за публикацию уровня У1, руб.
    level_2: int = Field(gt=0)  # сумма за публикацию уровня У2, руб.
    person_cap: int = Field(gt=0)  # предел на одного сотрудника, руб.
    fund: int = Field(gt=0)  # фонд премирования кафедры, руб.

    @model_validator(mode="after")
    def check_amounts(self) -> "Bonus":
        if self.level_1 < self.level_2:
            raise ValueError("сумма за У1 меньше суммы за У2")
        return self


class Matching(BaseModel):
    """Правила сопоставления по названию (сходство в процентах)."""

    model_config = ConfigDict(strict=True)
    auto_accept: int = Field(ge=0, le=100)  # принимается автоматически
    manual_review: int = Field(ge=0, le=100)  # направляется на проверку
    author_accept: int = Field(ge=0, le=100)  # автор — сотрудник
    author_review: int = Field(ge=0, le=100)  # автор — на проверку
    abbreviations: dict[str, str] = {}  # сокращение -> полное слово

    @model_validator(mode="after")
    def check_thresholds(self) -> "Matching":
        if self.manual_review > self.auto_accept:
            raise ValueError("порог проверки выше порога принятия")
        if self.author_review > self.author_accept:
            raise ValueError("порог проверки автора выше порога принятия")
        return self


def read_section(path: Path, name: str) -> dict[str, object]:
    """Читает раздел конфигурационного файла."""
    with path.open("rb") as file:
        data = tomllib.load(file)
    section: dict[str, object] = data[name]
    return section


def load_criteria(path: Path) -> Criteria:
    """Читает критерии из файла и проверяет их."""
    return Criteria.model_validate(read_section(path, "criteria"))


def load_quality(path: Path) -> Quality:
    """Читает требования к качеству данных."""
    return Quality.model_validate(read_section(path, "quality"))


def load_bonus(path: Path) -> Bonus:
    """Читает условия премирования."""
    return Bonus.model_validate(read_section(path, "bonus"))


def load_matching(path: Path) -> Matching:
    """Читает правила сопоставления по названию."""
    return Matching.model_validate(read_section(path, "matching"))


class Api(BaseModel):
    """Обращение к сервису метаданных публикаций."""

    model_config = ConfigDict(strict=True, str_strip_whitespace=True)
    base_url: str = Field(min_length=1)  # адрес сервиса
    mailto: str = Field(min_length=3)  # адрес для связи с владельцем
    timeout: float = Field(gt=0)  # наибольшее время ожидания ответа, с
    attempts: int = Field(ge=1, le=10)  # наибольшее число попыток
    backoff: float = Field(ge=0)  # задержка перед первым повтором, с
    max_wait: float = Field(ge=0)  # наибольшая задержка, с
    concurrency: int = Field(ge=1)  # наибольшее число запросов сразу


class Memo(BaseModel):
    """Реквизиты служебной записки на премирование."""

    model_config = ConfigDict(strict=True, str_strip_whitespace=True)
    recipient: str = Field(min_length=1)  # кому
    sender: str = Field(min_length=1)  # от кого
    signer: str = Field(min_length=1)  # должность подписывающего


def load_api(path: Path) -> Api:
    """Читает параметры обращения к сервису."""
    return Api.model_validate(read_section(path, "api"))


def load_memo(path: Path) -> Memo:
    """Читает реквизиты служебной записки."""
    return Memo.model_validate(read_section(path, "memo"))
