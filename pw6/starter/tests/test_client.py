"""Тесты обращения к сервису метаданных (заготовка, без сети: respx)."""

from typing import Any

import httpx
import respx

from src.client import FOUND, fetch_work, parse_response
from src.criteria import Api

BASE = "http://service.test"
API = Api(
    base_url=BASE,
    mailto="test@example.org",
    timeout=1.0,
    attempts=3,
    backoff=0.0,  # в тестах повтор без задержки
    max_wait=0.0,
    concurrency=2,
)
WORK = {
    "DOI": "10.1/a",
    "title": ["Статья"],
    "issued": {"date-parts": [[2025]]},
}


def answer(code: int, **details: Any) -> httpx.Response:
    """Ответ сервиса с запросом (нужен для raise_for_status)."""
    request = httpx.Request("GET", f"{BASE}/works/10.1/a")
    return httpx.Response(code, request=request, **details)


def ok() -> httpx.Response:
    return answer(200, json={"status": "ok", "message": WORK})


def fetch(doi: str = "10.1/a") -> tuple[str, int]:
    with httpx.Client(base_url=BASE) as client:
        result = fetch_work(client, doi, API)
    return result.status, result.attempts


def test_parse_response_found() -> None:
    assert parse_response(ok()) == WORK


@respx.mock
def test_fetch_work_found() -> None:
    respx.get(f"{BASE}/works/10.1/a").mock(return_value=ok())
    assert fetch() == (FOUND, 1)
