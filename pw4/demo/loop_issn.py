"""Перебор строк и операция над столбцом на выгрузке из 100 000 записей.

Запуск из корня проекта: uv run python -m sandbox.loop_issn
"""

import time

import pandas as pd

from src.normalize import normalize_issn
from src.tables import normalize_issn_column

pub = pd.read_parquet("data/raw/publications.parquet")
print(f"Строк в выгрузке: {len(pub)}")

# 1. Перебор строк с функцией из работы 2
try:
    for _, row in pub.iterrows():
        normalize_issn(row["issn"])
except AttributeError as error:
    print(f"1. Перебор строк: {type(error).__name__}: {error}")

# 2. Перебор строк с проверкой пропуска
start = time.perf_counter()
by_rows = []
for _, row in pub.iterrows():
    value = row["issn"]
    by_rows.append(None if pd.isna(value) else normalize_issn(value))
loop_time = time.perf_counter() - start
print(f"2. Перебор строк с проверкой pd.isna: {loop_time:.2f} с")

# 3. Операция над столбцом
try:
    start = time.perf_counter()
    by_column = normalize_issn_column(pub["issn"])
    column_time = time.perf_counter() - start
except NotImplementedError:
    print("3. Функция normalize_issn_column ещё не реализована")
else:
    expected = pd.Series(by_rows, dtype="str")
    differ = (expected.fillna("-") != by_column.fillna("-")).sum()
    print(f"3. Операция над столбцом: {column_time:.3f} с")
    print(f"   ускорение: в {loop_time / column_time:.0f} раз")
    print(f"   пропусков после нормализации: {by_column.isna().sum()}")
    print(f"   расхождений с перебором строк: {differ}")
