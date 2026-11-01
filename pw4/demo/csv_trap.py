"""Справочник, сохранённый табличным редактором, и проверка доли.

Запуск из корня проекта: uv run python -m sandbox.csv_trap
"""

from pathlib import Path

import pandas as pd

from src.tables import (
    check_share,
    merge_registry,
    normalize_issn_column,
    read_registry,
)

# 1. CSV и Parquet: что сохраняется при записи и чтении
table = pd.DataFrame({"issn": ["00406090", "03785955"]})
table.to_csv("sandbox/issn.csv", index=False)
table.to_parquet("sandbox/issn.parquet", index=False)
print("1. CSV:    ", pd.read_csv("sandbox/issn.csv")["issn"].tolist())
print("   Parquet:", pd.read_parquet("sandbox/issn.parquet")["issn"].tolist())

# 2. Справочник после открытия и сохранения в табличном редакторе
pub = pd.read_parquet("data/raw/publications.parquet")
pub["issn"] = normalize_issn_column(pub["issn"])
for name in ("data/reference/journals.csv", "sandbox/journals_excel.csv"):
    matched, unmatched = merge_registry(pub, read_registry(Path(name)))
    print(f"2. {name}: сопоставлено {len(matched)}")
    try:
        share = check_share(len(matched), len(pub), 0.9)
        print(f"   доля {share:.4f} — порог пройден")
    except ValueError as error:
        print(f"   ValueError: {error}")
