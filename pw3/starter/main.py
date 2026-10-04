"""Запуск проверки публикаций кафедры."""

import logging
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from src.criteria import load_criteria
from src.pipeline import Paths, run_check
from src.reporting import save_report


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        filename="data/output/check.log",
        encoding="utf-8",
    )
    criteria = load_criteria(Path("config/criteria.toml"))
    paths = Paths(
        publications=Path("data/raw/crossref_sample.json"),
        registry=Path("data/reference/registry.csv"),
    )
    today = datetime.now(ZoneInfo("Europe/Moscow")).date()
    report = run_check(paths, criteria, today)
    save_report(report, Path("data/output"))
    print(report.memo)


if __name__ == "__main__":
    main()
