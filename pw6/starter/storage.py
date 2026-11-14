"""Хранилище SQLite: ответы сервиса (кэш) и история запусков."""

import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.client import WorkResult
from src.criteria import Api
from src.verify import CONFIRMED

SCHEMA = """
CREATE TABLE IF NOT EXISTS responses (
    doi TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    body TEXT,
    fetched_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    registry_version TEXT NOT NULL,
    registry_sha256 TEXT NOT NULL,
    config_sha256 TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS decisions (
    run_id INTEGER NOT NULL REFERENCES runs (id),
    doi TEXT NOT NULL,
    decision TEXT NOT NULL,
    reason TEXT NOT NULL,
    PRIMARY KEY (run_id, doi)
);
"""


def now() -> str:
    """Текущее время с часовым поясом: 2026-11-20 10:15:00+03:00."""
    return datetime.now().astimezone().isoformat(sep=" ", timespec="seconds")


def connect(path: Path) -> sqlite3.Connection:
    """Открывает базу данных и создаёт таблицы, если их нет."""
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.executescript(SCHEMA)
    return connection


# Кэш ответов сервиса


def save_result(connection: sqlite3.Connection, result: WorkResult) -> None:
    """Сохраняет ответ; «сервис недоступен» не сохраняется."""
    raise NotImplementedError


def load_cached(
    connection: sqlite3.Connection, dois: list[str]
) -> dict[str, WorkResult]:
    """Сохранённые ответы для списка DOI: DOI -> результат."""
    raise NotImplementedError


async def fetch_cached(
    connection: sqlite3.Connection, dois: list[str], api: Api
) -> list[WorkResult]:
    """Ответы из кэша; недостающие запрашиваются у сервиса и сохраняются."""
    raise NotImplementedError


# История запусков


def file_sha256(path: Path) -> str:
    """Контрольная сумма SHA-256 содержимого файла."""
    raise NotImplementedError


def start_run(
    connection: sqlite3.Connection,
    registry_version: str,
    registry: Path,
    config: Path,
) -> int:
    """Записывает запуск и возвращает его номер."""
    raise NotImplementedError


def save_decisions(
    connection: sqlite3.Connection, run_id: int, decisions: pd.DataFrame
) -> None:
    """Записывает решения запуска (столбцы doi, decision, reason)."""
    raise NotImplementedError


def history(connection: sqlite3.Connection) -> pd.DataFrame:
    """Запуски с числом подтверждённых и неподтверждённых публикаций."""
    query = """
        SELECT r.id, r.started_at, r.registry_version,
               substr(r.registry_sha256, 1, 12) AS registry_sha256,
               substr(r.config_sha256, 1, 12) AS config_sha256,
               sum(d.decision = ?) AS confirmed,
               sum(d.decision <> ?) AS not_confirmed
        FROM runs AS r LEFT JOIN decisions AS d ON d.run_id = r.id
        GROUP BY r.id ORDER BY r.id
    """
    return pd.read_sql_query(query, connection, params=(CONFIRMED, CONFIRMED))


def run_info(connection: sqlite3.Connection, run_id: int) -> pd.Series:
    """Сведения об одном запуске."""
    runs = pd.read_sql_query(
        "SELECT * FROM runs WHERE id = ?", connection, params=(run_id,)
    )
    if runs.empty:
        raise ValueError(f"запуск {run_id} не найден")
    return runs.iloc[0]


def last_run(connection: sqlite3.Connection) -> int | None:
    row = connection.execute("SELECT max(id) FROM runs").fetchone()
    return None if row[0] is None else int(row[0])


def run_decisions(connection: sqlite3.Connection, run_id: int) -> pd.DataFrame:
    """Решения по публикациям одного запуска."""
    return pd.read_sql_query(
        "SELECT doi, decision, reason FROM decisions WHERE run_id = ?",
        connection,
        params=(run_id,),
    )


# Основной уровень: сравнение двух запусков


def compare_runs(
    connection: sqlite3.Connection, first: int, second: int
) -> pd.DataFrame:
    """Публикации, решение по которым в двух запусках различается."""
    raise NotImplementedError
