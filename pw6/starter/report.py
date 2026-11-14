"""Сверка с сервисом метаданных, служебная записка и история запусков.

Запуск из корня проекта:
    uv run python report.py verify   — сверка премируемых публикаций
    uv run python report.py memo     — служебная записка по последней сверке
    uv run python report.py history  — история запусков сверки
Коды возврата: 0 — успешно; 1 — нет исходных данных; 2 — сервис недоступен.
"""

import argparse
import asyncio
import sys
from contextlib import closing
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from src.client import UNAVAILABLE, service_available
from src.criteria import load_api, load_bonus, load_criteria, load_memo
from src.memo import MemoInfo, memo_context, render_memo
from src.storage import (
    compare_runs,
    connect,
    fetch_cached,
    history,
    last_run,
    load_cached,
    run_decisions,
    run_info,
    save_decisions,
    start_run,
)
from src.verify import (
    CONFIRMED,
    NO_ANSWER,
    NOT_IN_SERVICE,
    YEAR_MISMATCH,
    confirmed_rows,
    distribute,
    review_rows,
    verify_rows,
)

CONFIG = Path("config/criteria.toml")
REGISTRY = Path("data/reference/journals.csv")
OUTPUT = Path("data/output")
DATABASE = OUTPUT / "publications.db"
TEMPLATE = Path("templates/memo.docx")
DECISIONS = [CONFIRMED, NOT_IN_SERVICE, YEAR_MISMATCH, NO_ANSWER]


def read_rows() -> pd.DataFrame:
    """Строки «публикация — сотрудник» — результат allocate.py."""
    path = OUTPUT / "bonus_rows.csv"
    if not path.exists():
        raise FileNotFoundError(f"нет файла {path}: запустите allocate.py")
    return pd.read_csv(path, dtype={"staff_id": str})


def print_payments(rows: pd.DataFrame, paid: pd.DataFrame) -> None:
    print(
        f"Строк «публикация — сотрудник»: {len(rows)}, "
        f"сотрудников: {len(paid)}"
    )
    print(
        f"Начислено: {paid['accrued'].sum()} руб., с учётом предела: "
        f"{paid['capped'].sum()} руб."
    )
    print(
        f"Доля: {paid['share'].iloc[0]:.4f}, "
        f"выплачивается: {paid['paid'].sum()} руб."
    )


def verify(args: argparse.Namespace) -> int:
    """Сверка с сервисом, решения в истории, новое распределение фонда."""
    api = load_api(CONFIG)
    if not service_available(api):
        print(f"Сервис метаданных недоступен: {api.base_url}", file=sys.stderr)
        return 2
    criteria, bonus = load_criteria(CONFIG), load_bonus(CONFIG)
    rows = read_rows()
    dois = rows["doi"].drop_duplicates().tolist()
    with closing(connect(DATABASE)) as connection:
        cached = len(load_cached(connection, dois))
        results = asyncio.run(fetch_cached(connection, dois, api))
        decisions = verify_rows(rows, results)
        version = criteria.registry_version
        run_id = start_run(connection, version, REGISTRY, CONFIG)
        save_decisions(connection, run_id, decisions)
    print(f"Запуск сверки № {run_id}")
    print(
        f"Публикаций: {len(dois)}, из кэша: {cached}, "
        f"запрошено у сервиса: {len(dois) - cached}"
    )
    counts = decisions["decision"].value_counts()
    for decision in DECISIONS:
        print(f"  {decision}: {counts.get(decision, 0)}")
    review = review_rows(rows, decisions)
    review.to_csv(OUTPUT / "review_service.csv", index=False)
    print(f"На ручную проверку: {review['doi'].nunique()} публикаций")
    confirmed = confirmed_rows(rows, decisions)
    paid = distribute(confirmed, bonus)
    paid.to_csv(OUTPUT / "bonus_verified.csv", index=False)
    print_payments(confirmed, paid)
    if all(result.status == UNAVAILABLE for result in results):
        print("Сервис не ответил ни на один запрос", file=sys.stderr)
        return 2
    return 0


def memo(args: argparse.Namespace) -> int:
    """Служебная записка по последнему запуску сверки."""
    with closing(connect(DATABASE)) as connection:
        run_id = last_run(connection)
        if run_id is None:
            print("Нет запусков сверки: выполните report.py verify")
            return 1
        run = run_info(connection, run_id)
        decisions = run_decisions(connection, run_id)
    criteria, bonus = load_criteria(CONFIG), load_bonus(CONFIG)
    paid = distribute(confirmed_rows(read_rows(), decisions), bonus)
    info = MemoInfo(
        memo=load_memo(CONFIG),
        criteria=criteria,
        bonus=bonus,
        run_id=run_id,
        registry_sha256=str(run["registry_sha256"]),
        review=int((decisions["decision"] != CONFIRMED).sum()),
        today=args.date,
    )
    path = OUTPUT / "memo.docx"
    render_memo(TEMPLATE, memo_context(paid, info), path)
    total = paid["paid"].sum()
    print(f"Служебная записка: {path} (запуск № {run_id}, {total} руб.)")
    return 0


def show_history(args: argparse.Namespace) -> int:
    with closing(connect(DATABASE)) as connection:
        runs = history(connection)
    if runs.empty:
        print("Запусков сверки нет")
        return 0
    print(runs.to_string(index=False))
    return 0


def compare(args: argparse.Namespace) -> int:
    """Основной уровень: что изменилось между двумя запусками."""
    with closing(connect(DATABASE)) as connection:
        changes = compare_runs(connection, args.first, args.second)
    if changes.empty:
        print(f"Решения запусков {args.first} и {args.second} совпадают")
    else:
        print(changes.to_string(index=False))
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("verify", help="сверка с сервисом метаданных")
    memo_parser = commands.add_parser("memo", help="служебная записка")
    memo_parser.add_argument(
        "--date",
        type=date.fromisoformat,
        default=datetime.now().astimezone().date(),
        help="дата записки ГГГГ-ММ-ДД (по умолчанию — сегодня)",
    )
    commands.add_parser("history", help="история запусков сверки")
    compare_parser = commands.add_parser("compare", help="сравнение запусков")
    compare_parser.add_argument("first", type=int)
    compare_parser.add_argument("second", type=int)
    return parser.parse_args(argv)


COMMANDS = {
    "verify": verify,
    "memo": memo,
    "history": show_history,
    "compare": compare,
}


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        return COMMANDS[args.command](args)
    except FileNotFoundError as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
