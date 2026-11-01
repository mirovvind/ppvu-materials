"""Сведение выгрузки со справочниками и предварительный расчёт премий."""

import logging
from pathlib import Path

import pandas as pd

from src.bonus import bonus_table, summary_by_person
from src.criteria import load_bonus, load_criteria, load_quality
from src.tables import (
    MatchedPublications,
    check_share,
    merge_registry,
    normalize_issn_column,
    read_registry,
)

CONFIG = Path("config/criteria.toml")
OUTPUT = Path("data/output")


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        filename=OUTPUT / "check.log",
        encoding="utf-8",
    )
    criteria = load_criteria(CONFIG)
    quality = load_quality(CONFIG)
    bonus = load_bonus(CONFIG)

    publications = pd.read_parquet("data/raw/publications.parquet")
    publications["issn"] = normalize_issn_column(publications["issn"])
    registry = read_registry(Path("data/reference/journals.csv"))
    matched, unmatched = merge_registry(publications, registry)
    share = check_share(len(matched), len(publications), quality.min_share)
    MatchedPublications.validate(matched, lazy=True)
    matched.to_parquet(OUTPUT / "matched.parquet", index=False)
    unmatched.to_parquet(OUTPUT / "unmatched.parquet", index=False)
    print(f"Публикаций в выгрузке: {len(publications)}")
    print(f"Сопоставлено со справочником: {len(matched)} (доля {share:.4f})")
    print(f"Не сопоставлено: {len(unmatched)}")

    authorships = pd.read_parquet("data/raw/authorships.parquet")
    staff = pd.read_csv("data/reference/staff.csv", dtype=str)
    rows = bonus_table(matched, authorships, staff, criteria, bonus)
    rows.to_parquet(OUTPUT / "bonus.parquet", index=False)
    summary = summary_by_person(rows)
    summary.to_csv(OUTPUT / "bonus_draft.csv", index=False)
    print(f"Кафедра: {bonus.department}")
    print(f"Публикаций к премированию: {rows['doi'].nunique()}")
    print(f"Сотрудников: {len(summary)}")
    print(f"Предварительная сумма: {rows['amount'].sum()} руб.")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
