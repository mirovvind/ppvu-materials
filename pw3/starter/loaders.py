"""Чтение выгрузок и входной контроль данных."""

import csv
import json
import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from src.models import Journal, Publication
from src.normalize import normalize_doi, normalize_issn

logger = logging.getLogger("publications")


class CrossrefAuthor(BaseModel):
    family: str
    given: str = ""


class CrossrefDate(BaseModel):
    date_parts: list[list[int | None]] = Field(alias="date-parts")


class CrossrefWork(BaseModel):
    doi: str = Field(alias="DOI")
    title: list[str] = Field(min_length=1)
    issn: list[str] = Field(default_factory=list, alias="ISSN")
    journal: list[str] = Field(default_factory=list, alias="container-title")
    authors: list[CrossrefAuthor] = Field(default_factory=list, alias="author")
    issued: CrossrefDate | None = None


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
    """Записывает перечень отклонённых записей в файл CSV."""
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["doi", "reason"])
        writer.writerows(rejected)


def get_year(work: CrossrefWork) -> int | None:
    """Возвращает год выхода или None."""
    if work.issued is None or not work.issued.date_parts:
        return None
    first = work.issued.date_parts[0]
    return first[0] if first else None


def to_publication(work: CrossrefWork) -> Publication:
    """Приводит запись Crossref к модели публикации."""
    issns = [normalize_issn(value) for value in work.issn]
    return Publication(
        title=work.title[0],
        year=get_year(work),
        doi=normalize_doi(work.doi),
        journal_title=work.journal[0] if work.journal else None,
        authors=[f"{a.family} {a.given}".strip() for a in work.authors],
        issns=[value for value in issns if value is not None],
    )


class OpenAlexSource(BaseModel):
    display_name: str | None = None
    issn_l: str | None = None
    issn: list[str] | None = None


class OpenAlexLocation(BaseModel):
    source: OpenAlexSource | None = None


class OpenAlexWork(BaseModel):
    doi: str | None = None
    title: str | None = None
    publication_year: int | None = None
    primary_location: OpenAlexLocation | None = None


def openalex_to_publication(work: OpenAlexWork) -> Publication:
    """Приводит запись OpenAlex к модели публикации."""
    source = work.primary_location.source if work.primary_location else None
    issns = [normalize_issn(v) for v in (source.issn or [])] if source else []
    return Publication(
        title=work.title or "",
        year=work.publication_year,
        doi=normalize_doi(work.doi),
        journal_title=source.display_name if source else None,
        issns=[value for value in issns if value is not None],
    )


def find_duplicates(publications: list[Publication]) -> list[str]:
    """Возвращает DOI, встречающиеся более одного раза."""
    counts: dict[str, int] = {}
    for item in publications:
        if item.doi is not None:
            counts[item.doi] = counts.get(item.doi, 0) + 1
    return [doi for doi, count in counts.items() if count > 1]


def check_publications(
    records: list[dict[str, Any]],
) -> tuple[list[Publication], list[tuple[Any, str]]]:
    """Входной контроль и приведение записей к модели публикации."""
    accepted, rejected = check_records(records)
    publications: list[Publication] = []
    for work in accepted:
        try:
            publications.append(to_publication(work))
        except ValueError as error:  # штатная ситуация: запись отклоняется
            rejected.append((work.doi, str(error)))
    logger.info("принято: %d, отклонено: %d", len(publications), len(rejected))
    return publications, rejected


def load_registry_rows(path: Path) -> list[str]:
    """Читает строки справочника без заголовка.

    Отсутствие файла и пустой файл — ошибки: функция вызывает
    исключения FileNotFoundError и ValueError (п. 3.3 лекции 3).
    """
    raise NotImplementedError


def load_registry(path: Path) -> dict[str, Journal]:
    """Строит справочник изданий: ISSN -> издание."""
    registry: dict[str, Journal] = {}
    for title, issn_print, issn_online, level in csv.reader(
        load_registry_rows(path)
    ):
        journal = Journal(
            title=title,
            issn_print=normalize_issn(issn_print),
            issn_online=normalize_issn(issn_online),
            level=int(level) if level else None,  # пусто — не указан
        )
        for issn in (journal.issn_print, journal.issn_online):
            if issn is not None:
                registry[issn] = journal
    return registry
