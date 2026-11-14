"""Последовательная загрузка с обработкой отказов сервиса.

Запуск: uv run python -m sandbox.fetch_sync
"""

import time
from collections import Counter

from sandbox.demo_tools import not_written, premium_dois, reset, settings
from src.client import FOUND, fetch_all

if __name__ == "__main__":
    api = settings()
    reset(api)
    dois = premium_dois()
    start = time.perf_counter()
    try:
        results = fetch_all(dois, api)
    except NotImplementedError as error:
        raise SystemExit(f"Функция {not_written(error)} ещё не написана")
    seconds = time.perf_counter() - start
    print("Не с первой попытки или не найдены (DOI, результат, попыток):")
    for result in results:
        if result.status != FOUND or result.attempts > 1:
            print(f"  {result.doi}  {result.status:11}  {result.attempts}")
    counts = Counter(result.status for result in results)
    attempts = sum(result.attempts for result in results)
    print(f"Итог: {dict(counts)}; обращений к сервису: {attempts}")
    print(f"Время последовательной загрузки: {seconds:.1f} с")
