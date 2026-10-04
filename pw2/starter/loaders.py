"""Чтение выгрузок и входной контроль данных."""

import csv  # noqa: F401 — понадобится в функции save_rejected
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError


class CrossrefWork(BaseModel):
    doi: str = Field(alias="DOI")
    title: list[str] = Field(min_length=1)
    issn: list[str] = Field(default_factory=list, alias="ISSN")
    journal: list[str] = Field(default_factory=list, alias="container-title")


def load_items(path: Path) -> list[dict[str, Any]]:
    """Читает файл ответа Crossref и возвращает список записей."""
    with path.open(encoding="utf-8") as file:
        data = json.load(file)
    items: list[dict[str, Any]] = data["message"]["items"]
    return items


def check_records(
    records: list[dict[str, Any]],
) -> tuple[list[CrossrefWork], list[tuple[Any, str]]]:
    """Делит записи на принятые и отклонённые."""
    accepted: list[CrossrefWork] = []
    rejected: list[tuple[Any, str]] = []
    for raw in records:
        try:
            accepted.append(CrossrefWork.model_validate(raw))
        except ValidationError as error:
            first = error.errors()[0]
            field_name = ".".join(str(p) for p in first["loc"])
            rejected.append((raw.get("DOI"), f"{field_name}: {first['msg']}"))
    return accepted, rejected


def save_rejected(rejected: list[tuple[Any, str]], path: Path) -> None:
    """Записывает перечень отклонённых записей в файл CSV.

    Первая строка файла — заголовок doi,reason; далее по строке
    на каждую отклонённую запись.
    """
    raise NotImplementedError
