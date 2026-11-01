"""Соединение выгрузки со справочником по печатному ISSN.

Запуск из корня проекта: uv run python -m sandbox.naive_merge
"""

from pathlib import Path

import pandas as pd

from src.tables import normalize_issn_column, read_registry

pub = pd.read_parquet("data/raw/publications.parquet")
pub["issn"] = normalize_issn_column(pub["issn"])
registry = read_registry(Path("data/reference/journals.csv"))
print(f"Публикаций: {len(pub)}, строк справочника: {len(registry)}")
print(f"Изданий в справочнике: {registry['journal_id'].nunique()}")

# 1. Без проверки кратности
merged = pub.merge(registry, left_on="issn", right_on="issn_print", how="left")
found = merged.drop_duplicates("doi")["journal_id"].notna().sum()
print(f"1. Строк результата: {len(merged)}; публикаций с парой: {found}")

# 2. С проверкой кратности «многие к одному»
try:
    pub.merge(
        registry,
        left_on="issn",
        right_on="issn_print",
        how="left",
        validate="many_to_one",
    )
except pd.errors.MergeError as error:
    print(f"2. {type(error).__name__}: {error}")
