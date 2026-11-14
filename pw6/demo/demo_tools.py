"""Общие функции программ для опытов работы 6."""

from pathlib import Path
from typing import Any

import httpx
import pandas as pd

from src.criteria import Api, load_api

ROWS = Path("data/output/bonus_rows.csv")  # результат allocate.py


def settings() -> Api:
    return load_api(Path("config/criteria.toml"))


def premium_dois() -> list[str]:
    """DOI премируемых публикаций в порядке файла bonus_rows.csv."""
    return pd.read_csv(ROWS)["doi"].drop_duplicates().tolist()


def reset(api: Api) -> None:
    """Сценарий сервера-имитатора — с начала, счётчики — с нуля."""
    httpx.post(f"{api.base_url}/reset").raise_for_status()


def stats(api: Api) -> dict[str, Any]:
    """Счётчики сервера-имитатора: обращения и коды ответов."""
    data: dict[str, Any] = httpx.get(f"{api.base_url}/stats").json()
    return data


def not_written(error: BaseException) -> str:
    """Имя функции, в которой вызвано исключение NotImplementedError."""
    where = error.__traceback__
    while where is not None and where.tb_next is not None:
        where = where.tb_next
    return where.tb_frame.f_code.co_name if where else "?"
