"""Тесты хранилища SQLite: кэш ответов и история запусков (заготовка)."""

from pathlib import Path

from src.client import FOUND, NOT_FOUND, UNAVAILABLE, WorkResult
from src.criteria import Api
from src.storage import connect, load_cached, save_result

BASE = "http://service.test"
API = Api(
    base_url=BASE,
    mailto="test@example.org",
    timeout=1.0,
    attempts=3,
    backoff=0.0,
    max_wait=0.0,
    concurrency=2,
)
WORK = {
    "DOI": "10.1/a",
    "title": ["Статья"],
    "issued": {"date-parts": [[2025]]},
}


def test_cache_keeps_found_and_not_found(tmp_path: Path) -> None:
    connection = connect(tmp_path / "test.db")
    save_result(connection, WorkResult("10.1/a", FOUND, WORK, 1))
    save_result(connection, WorkResult("10.1/b", NOT_FOUND, None, 1))
    save_result(connection, WorkResult("10.1/c", UNAVAILABLE, None, 4))
    cached = load_cached(connection, ["10.1/a", "10.1/b", "10.1/c"])
    assert sorted(cached) == ["10.1/a", "10.1/b"]  # недоступный не сохранён
    assert cached["10.1/a"].status == FOUND
    assert cached["10.1/a"].work == WORK
    assert cached["10.1/a"].attempts == 0  # ответ из кэша
    assert cached["10.1/b"].status == NOT_FOUND
