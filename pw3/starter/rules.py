"""Проверка критериев: решение по каждой публикации."""

from datetime import date

from src.criteria import Criteria
from src.matching import Match
from src.models import CheckResult, Decision


def decide(year: int, level: int | None, rules: Criteria) -> Decision:
    """Решение зависит только от аргументов функции.

    Реализуется в п. 4.3 указаний по пункту 3.1 лекции 3.
    """
    raise NotImplementedError


def explain(year: int, level: int | None, rules: Criteria) -> str:
    """Формулирует обоснование решения."""
    if not rules.year_from <= year <= rules.year_to:
        period = f"{rules.year_from}–{rules.year_to}"
        return f"год {year} вне отчётного периода {period}"
    if level is None:
        return "издание не найдено в справочнике"
    return f"уровень издания У{level}, пороговый уровень У{rules.max_level}"


def decide_all(
    matched: list[Match], rules: Criteria, today: date
) -> list[CheckResult]:
    """Принимает решение по каждой сопоставленной публикации."""
    results: list[CheckResult] = []
    for publication, journal, confidence in matched:
        level = journal.level if journal is not None else None
        if publication.year is None:  # штатная ситуация
            decision, reason = Decision.MANUAL, "год выхода не указан"
        else:
            decision = decide(publication.year, level, rules)
            reason = explain(publication.year, level, rules)
        results.append(
            CheckResult(
                doi=publication.doi,
                decision=decision,
                reason=reason,
                registry_version=rules.registry_version,
                checked_on=today,
                confidence=confidence,
            )
        )
    return results
