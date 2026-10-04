"""Конвейер обработки: связывает этапы проверки публикаций."""

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from src.criteria import Criteria
from src.loaders import check_publications, load_items, load_registry
from src.matching import match_publications
from src.reporting import Report, build_report
from src.rules import decide_all


@dataclass
class Paths:
    """Пути к исходным файлам."""

    publications: Path  # выгрузка публикаций
    registry: Path  # справочник изданий


def run_check(paths: Paths, criteria: Criteria, today: date) -> Report:
    """Выполняет проверку публикаций от загрузки данных до отчёта."""
    raw = load_items(paths.publications)  # чтение
    registry = load_registry(paths.registry)  # чтение
    publications, rejected = check_publications(raw)  # входной контроль
    matched = match_publications(publications, registry)  # сопоставление
    results = decide_all(matched, criteria, today)  # проверка
    return build_report(results, rejected, criteria)  # отчёт
