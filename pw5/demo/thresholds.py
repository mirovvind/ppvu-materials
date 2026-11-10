"""Точность и полнота сопоставления при разных порогах принятия."""

from pathlib import Path

import pandas as pd

from src.criteria import load_matching
from src.matching import match_titles, quality
from src.tables import read_registry

rules = load_matching(Path("config/criteria.toml"))
labels = pd.read_csv("data/raw/labels.csv", dtype=str)
registry = read_registry(Path("data/reference/journals.csv"))
journals = registry.drop_duplicates("journal_id").reset_index(drop=True)
found = match_titles(labels["container_title"].tolist(), journals, rules)
print(
    f"Размечено названий: {len(labels)}, "
    f"из них есть в справочнике: {labels['journal_id'].notna().sum()}"
)
print("Порог  Принято  Точность  Полнота")
for threshold in range(75, 101, 5):
    accepted = ((found["score"] >= threshold) & found["same_numbers"]).sum()
    precision, recall = quality(found, labels, threshold)
    print(f"{threshold:5}  {accepted:7}  {precision:8.3f}  {recall:7.3f}")
