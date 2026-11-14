"""Кэш ответов сервиса в SQLite: повторный запуск.

Запуск: uv run python -m sandbox.cache_demo
"""

import asyncio
import time
from contextlib import closing
from pathlib import Path

from sandbox.demo_tools import (
    not_written,
    premium_dois,
    reset,
    settings,
    stats,
)
from src.storage import connect, fetch_cached

DATABASE = Path("data/output/demo_cache.db")  # отдельная база для опыта

if __name__ == "__main__":
    api = settings()
    dois = premium_dois()
    DATABASE.unlink(missing_ok=True)
    reset(api)
    with closing(connect(DATABASE)) as connection:
        for run in (1, 2):
            before = stats(api)["requests"]
            start = time.perf_counter()
            try:
                results = asyncio.run(fetch_cached(connection, dois, api))
            except NotImplementedError as error:
                raise SystemExit(
                    f"Функция {not_written(error)} ещё не написана"
                )
            seconds = time.perf_counter() - start
            cached = sum(result.attempts == 0 for result in results)
            requests = stats(api)["requests"] - before
            print(
                f"Запуск {run}: из кэша {cached}, обращений к серверу "
                f"{requests}, {seconds:.1f} с"
            )
        query = "SELECT status, count(*) FROM responses GROUP BY status"
        print(f"В кэше: {dict(connection.execute(query).fetchall())}")
