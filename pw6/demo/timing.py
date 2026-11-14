"""Последовательная и асинхронная загрузка; запросы без ограничения.

Запуск: uv run python -m sandbox.timing
С ограничением в один запрос: uv run python -m sandbox.timing --limit 1
"""

import asyncio
import sys
import time
from collections import Counter

import httpx

from sandbox.demo_tools import not_written, premium_dois, reset, settings
from src.client import WorkResult, fetch_all, fetch_all_async


async def all_at_once(base_url: str, dois: list[str]) -> Counter[int]:
    """Все запросы сразу, без семафора и без повторов: коды ответов."""
    async with httpx.AsyncClient(base_url=base_url, timeout=30) as client:
        tasks = [client.get(f"/works/{doi}") for doi in dois]
        responses = await asyncio.gather(*tasks)
    return Counter(response.status_code for response in responses)


def show(title: str, start: float, results: list[WorkResult]) -> None:
    seconds = time.perf_counter() - start
    attempts = sum(result.attempts for result in results)
    print(f"{title}: {seconds:.1f} с, обращений к сервису: {attempts}")


if __name__ == "__main__":
    api = settings()
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])
        api = api.model_copy(update={"concurrency": limit})
    dois = premium_dois()
    print(f"Публикаций: {len(dois)}, одновременно: {api.concurrency}")
    try:
        reset(api)
        start = time.perf_counter()
        show("Последовательно", start, fetch_all(dois, api))
        reset(api)
        start = time.perf_counter()
        show("Асинхронно", start, asyncio.run(fetch_all_async(dois, api)))
    except NotImplementedError as error:
        raise SystemExit(f"Функция {not_written(error)} ещё не написана")
    reset(api)
    codes = asyncio.run(all_at_once(api.base_url, dois))
    print(f"Все запросы сразу, без семафора: {dict(sorted(codes.items()))}")
