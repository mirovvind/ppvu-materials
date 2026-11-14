"""Обращение к сервису метаданных публикаций (подобие Crossref)."""

import asyncio
import os
from dataclasses import dataclass
from typing import Any

import httpx
from tenacity import (
    RetryCallState,
    retry_if_exception_type,
    stop_after_attempt,
)

from src.criteria import Api

FOUND = "found"  # сведения получены
NOT_FOUND = "not_found"  # публикации нет в сервисе (ответ 404)
UNAVAILABLE = "unavailable"  # сервис не ответил за все попытки
MAILTO = "PUBLICATIONS_MAILTO"  # переменная окружения: адрес для связи


@dataclass
class WorkResult:
    """Результат запроса сведений об одной публикации."""

    doi: str
    status: str  # FOUND, NOT_FOUND или UNAVAILABLE
    work: dict[str, Any] | None = None  # раздел message ответа сервиса
    attempts: int = 0  # число обращений к сервису; 0 — ответ из кэша


class Retryable(Exception):
    """Временный отказ сервиса (429, 5xx): запрос стоит повторить."""

    def __init__(self, code: int, retry_after: float | None) -> None:
        super().__init__(f"сервис ответил {code}")
        self.code = code
        self.retry_after = retry_after  # заголовок Retry-After, с


RETRY_ON = (Retryable, httpx.TransportError)  # ошибки, после которых повтор


def headers(api: Api) -> dict[str, str]:
    """Заголовки запроса: программа и адрес для связи с её владельцем."""
    mailto = os.environ.get(MAILTO, api.mailto)
    return {"User-Agent": f"publications/0.1 (mailto:{mailto})"}


def make_client(api: Api) -> httpx.Client:
    return httpx.Client(
        base_url=api.base_url, timeout=api.timeout, headers=headers(api)
    )


def make_async_client(api: Api) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=api.base_url, timeout=api.timeout, headers=headers(api)
    )


def retry_after(response: httpx.Response) -> float | None:
    """Значение заголовка Retry-After в секундах или None."""
    value = response.headers.get("Retry-After")
    try:
        return float(value) if value is not None else None
    except ValueError:  # дата вместо числа секунд: ждать по общему правилу
        return None


def parse_response(response: httpx.Response) -> dict[str, Any] | None:
    """Сведения о публикации; None — публикации нет в сервисе."""
    raise NotImplementedError


def delay(api: Api, error: BaseException | None, attempt: int) -> float:
    """Задержка перед повтором после попытки с номером attempt, с."""
    raise NotImplementedError


def retry_options(api: Api) -> dict[str, Any]:
    """Правила повтора запроса для tenacity."""

    def wait(state: RetryCallState) -> float:
        error = state.outcome.exception() if state.outcome else None
        return delay(api, error, state.attempt_number)

    return {
        "stop": stop_after_attempt(api.attempts),
        "wait": wait,
        "retry": retry_if_exception_type(RETRY_ON),
        "reraise": True,  # после последней попытки — исходное исключение
    }


def fetch_work(client: httpx.Client, doi: str, api: Api) -> WorkResult:
    """Сведения об одной публикации с повторами; исключений не вызывает."""
    raise NotImplementedError


def fetch_all(dois: list[str], api: Api) -> list[WorkResult]:
    """Последовательная загрузка: следующий запрос — после ответа."""
    with make_client(api) as client:
        return [fetch_work(client, doi, api) for doi in dois]


async def fetch_work_async(
    client: httpx.AsyncClient, doi: str, api: Api, limit: asyncio.Semaphore
) -> WorkResult:
    """То же, что fetch_work; одновременных запросов не больше limit."""
    raise NotImplementedError


async def fetch_all_async(dois: list[str], api: Api) -> list[WorkResult]:
    """Асинхронная загрузка; порядок результатов совпадает с порядком DOI."""
    raise NotImplementedError


def service_available(api: Api) -> bool:
    """Отвечает ли сервис вообще (одна попытка, без повторов)."""
    try:
        with make_client(api) as client:
            return client.get("/works", params={"rows": 0}).is_success
    except httpx.TransportError:
        return False
