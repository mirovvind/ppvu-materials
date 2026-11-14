"""Расширенный уровень: сведения о публикации из Crossref и OpenAlex.

Запуск: uv run python -m sandbox.live 10.1038/nature12373
Перед запуском задать адрес для связи (вежливый пул сервисов):
    export PUBLICATIONS_MAILTO=student@example.org
Программа обращается к настоящим сервисам; самопроверка её не запускает.
"""

import os
import sys

import httpx

from sandbox.demo_tools import settings
from src.client import MAILTO, fetch_work, headers, make_client
from src.criteria import Api
from src.loaders import (
    CrossrefWork,
    OpenAlexWork,
    openalex_to_publication,
    to_publication,
)
from src.models import Publication

CROSSREF = "https://api.crossref.org"
OPENALEX = "https://api.openalex.org"


def from_crossref(doi: str, api: Api) -> Publication | None:
    """Запрос к Crossref функцией fetch_work (с повторами)."""
    live = api.model_copy(update={"base_url": CROSSREF})
    with make_client(live) as client:
        result = fetch_work(client, doi, live)
    print(f"Crossref: {result.status}, попыток: {result.attempts}")
    if result.work is None:
        return None
    return to_publication(CrossrefWork.model_validate(result.work))


def from_openalex(doi: str, api: Api) -> Publication | None:
    """Запрос к OpenAlex: ответ — сама запись, без раздела message."""
    params = {"mailto": os.environ.get(MAILTO, api.mailto)}
    with httpx.Client(
        base_url=OPENALEX, timeout=api.timeout, headers=headers(api)
    ) as client:
        response = client.get(f"/works/doi:{doi}", params=params)
    print(f"OpenAlex: код ответа {response.status_code}")
    if response.status_code == 404:
        return None
    response.raise_for_status()
    work = OpenAlexWork.model_validate(response.json())
    return openalex_to_publication(work)


if __name__ == "__main__":
    doi = sys.argv[1] if len(sys.argv) > 1 else "10.1038/nature12373"
    api = settings()
    if MAILTO not in os.environ:
        print(f"Задайте адрес для связи: export {MAILTO}=...")
    for publication in (from_crossref(doi, api), from_openalex(doi, api)):
        print(f"  {publication}")
