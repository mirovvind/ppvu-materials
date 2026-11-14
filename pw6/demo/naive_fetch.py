"""Наивная загрузка: цикл запросов без обработки ошибок.

Запуск (сервер-имитатор запущен во втором терминале):
    uv run python -m sandbox.naive_fetch
"""

import httpx

from sandbox.demo_tools import premium_dois, reset, settings

api = settings()
reset(api)
dois = premium_dois()
print(f"Публикаций: {len(dois)}")
for number, doi in enumerate(dois, start=1):
    response = httpx.get(f"{api.base_url}/works/{doi}")
    response.raise_for_status()  # код ответа не 2xx — исключение
    work = response.json()["message"]
    year = work["issued"]["date-parts"][0][0]
    print(f"{number:3}  {doi}  {year}  {work['container-title'][0][:40]}")
print("Все публикации загружены")
