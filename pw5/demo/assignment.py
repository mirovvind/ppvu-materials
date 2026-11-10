"""Жадный алгоритм и задача о назначениях на двух названиях."""

from pathlib import Path

import numpy as np
from rapidfuzz import fuzz, process

from src.criteria import load_matching
from src.matching import assign, greedy, normalize_title

EXPORT = [
    "Тр. Малозаводского гос. университета",
    "Тр. Малозаводского аграрного ун-та",
]
REGISTRY = [
    "Труды Малозаводского государственного университета",
    "Труды Малозаводского аграрного университета",
]

words = load_matching(Path("config/criteria.toml")).abbreviations
query = [normalize_title(title, words) for title in EXPORT]
names = [normalize_title(title, words) for title in REGISTRY]
scores = process.cdist(query, names, scorer=fuzz.ratio)
print("Сходство, % (строки — выгрузка, столбцы — справочник):")
print(np.round(scores, 1))
for name, method in (("Жадный алгоритм", greedy), ("Назначения", assign)):
    pairs = method(scores)
    total = sum(scores[i, j] for i, j in pairs)
    print(f"{name}: сумма {total:.1f}")
    for i, j in pairs:
        print(f"  {EXPORT[i]}  ->  {REGISTRY[j]}")
