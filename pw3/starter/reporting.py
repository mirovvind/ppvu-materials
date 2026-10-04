"""Формирование служебной записки и протокола проверки."""

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.criteria import Criteria
from src.loaders import save_rejected
from src.models import CheckResult, Decision


@dataclass
class Report:
    """Результат проверки: служебная записка и протокол."""

    memo: str  # текст служебной записки
    protocol: list[CheckResult]  # решение по каждой публикации
    rejected: list[tuple[Any, str]]  # перечень отклонённых записей


def build_report(
    results: list[CheckResult],
    rejected: list[tuple[Any, str]],
    rules: Criteria,
) -> Report:
    """Составляет служебную записку по результатам проверки."""
    counts = {item: 0 for item in Decision}
    for result in results:
        counts[result.decision] += 1
    lines = [
        "Служебная записка о результатах проверки публикаций",
        f"Основание: {rules.basis}",
        f"Отчётный период: {rules.year_from}–{rules.year_to}",
        f"Справочник изданий: {rules.registry_version}",
        f"Засчитано: {counts[Decision.ACCEPTED]}",
        f"Не засчитано: {counts[Decision.REJECTED]}",
        f"Направлено на ручную проверку: {counts[Decision.MANUAL]}",
        f"Не допущено в обработку: {len(rejected)}",
    ]
    return Report("\n".join(lines) + "\n", results, rejected)


def save_report(report: Report, folder: Path) -> None:
    """Записывает служебную записку, протокол и перечень отклонённых."""
    (folder / "memo.txt").write_text(report.memo, encoding="utf-8")
    with (folder / "protocol.csv").open(
        "w", encoding="utf-8", newline=""
    ) as file:
        writer = csv.writer(file)
        writer.writerow(["doi", "decision", "reason", "confidence"])
        for item in report.protocol:
            writer.writerow(
                [item.doi, item.decision.value, item.reason, item.confidence]
            )
    save_rejected(report.rejected, folder / "rejected.csv")
