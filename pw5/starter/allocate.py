"""Нечёткое сопоставление, полный расчёт и распределение фонда."""

from pathlib import Path

import pandas as pd

from src.authors import match_authors, name_rows
from src.bonus import (
    accepted_publications,
    bonus_table,
    normalize_orcid_column,
)
from src.criteria import load_bonus, load_criteria, load_matching
from src.fund import best_share, payments, person_totals
from src.matching import AUTO, REVIEW, match_titles
from src.tables import read_registry

CONFIG = Path("config/criteria.toml")
OUTPUT = Path("data/output")


def main() -> None:
    criteria = load_criteria(CONFIG)
    bonus = load_bonus(CONFIG)
    rules = load_matching(CONFIG)

    # 1. Нечёткое сопоставление публикаций без пары
    matched = pd.read_parquet(OUTPUT / "matched.parquet")
    unmatched = pd.read_parquet(OUTPUT / "unmatched.parquet")
    containers = pd.read_parquet("data/raw/containers.parquet")
    registry = read_registry(Path("data/reference/journals.csv"))
    journals = registry.drop_duplicates("journal_id").reset_index(drop=True)
    unmatched = unmatched.merge(containers, on="doi", validate="one_to_one")
    titles = unmatched["container_title"].dropna().unique().tolist()
    found = match_titles(titles, journals, rules)
    found[found["status"] == REVIEW].to_csv(
        OUTPUT / "review_journals.csv", index=False
    )
    pairs = unmatched.merge(
        found[found["status"] == AUTO][["container_title", "journal_id"]],
        on="container_title",
        validate="many_to_one",
    )
    pairs = pairs.merge(
        journals[["journal_id", "level"]], on="journal_id", validate="m:1"
    )
    full = pd.concat([matched, pairs[matched.columns]], ignore_index=True)
    print(f"Названий без пары: {len(titles)}")
    print(
        f"Принято: {(found['status'] == AUTO).sum()}, "
        f"на проверку: {(found['status'] == REVIEW).sum()}"
    )
    print(f"Публикаций сопоставлено по названию: {len(pairs)}")

    # 2. Авторы: по ORCID и по фамилии и инициалам
    authorships = pd.read_parquet("data/raw/authorships.parquet")
    staff = pd.read_csv("data/reference/staff.csv", dtype=str)
    by_orcid = bonus_table(full, authorships, staff, criteria, bonus)
    accepted = accepted_publications(full, criteria, bonus)
    authors = authorships[authorships["doi"].isin(accepted["doi"])]
    no_orcid = authors[normalize_orcid_column(authors["orcid"]).isna()]
    people = staff[staff["department"] == bonus.department]
    by_name = match_authors(no_orcid, by_orcid, people, rules)
    by_name[by_name["status"] == REVIEW].to_csv(
        OUTPUT / "review_authors.csv", index=False
    )
    print(f"Найдено по ФИО: {(by_name['status'] == AUTO).sum()}")
    names = by_name[by_name["status"] == AUTO]
    rows = pd.concat(
        [
            by_orcid.assign(basis="ORCID"),
            name_rows(accepted, authorships, names).assign(basis="ФИО"),
        ],
        ignore_index=True,
    )
    if rows.duplicated(["doi", "staff_id"]).any():
        raise ValueError("сотрудник указан в публикации дважды")
    rows.to_csv(OUTPUT / "bonus_rows.csv", index=False)

    # 3. Распределение фонда
    totals = person_totals(rows, bonus.person_cap)
    share = best_share(totals["capped"].to_numpy(), bonus.fund)
    paid = payments(totals, share, bonus.fund)
    paid.to_csv(OUTPUT / "bonus_final.csv", index=False)
    print(
        f"Строк «публикация — сотрудник»: {len(rows)}, "
        f"сотрудников: {len(totals)}"
    )
    print(
        f"Начислено: {totals['accrued'].sum()} руб., с учётом предела: "
        f"{totals['capped'].sum()} руб."
    )
    print(
        f"Доля: {paid['share'].iloc[0]:.4f}, "
        f"выплачивается: {paid['paid'].sum()} руб. из {bonus.fund}"
    )
    print(paid.to_string(index=False))


if __name__ == "__main__":
    main()
