"""Распределение фонда премирования с учётом ограничений."""

import numpy as np
import pandas as pd

SCALE = 10_000  # доля записывается в десятитысячных: 0,8137 -> 8137


def person_totals(rows: pd.DataFrame, cap: int) -> pd.DataFrame:
    """Начислено каждому сотруднику и начисленное с учётом предела."""
    totals = rows.groupby(["staff_id", "full_name"], as_index=False).agg(
        accrued=("amount", "sum")
    )
    totals["capped"] = totals["accrued"].clip(upper=cap)
    return totals.sort_values("full_name").reset_index(drop=True)


def best_share(capped: np.ndarray, fund: int) -> float:
    """Наибольшая доля t: каждому не меньше t от начисленного.

    Переменные: выплаты y_1 ... y_n и доля t (последняя переменная).
    """
    raise NotImplementedError


def payments(totals: pd.DataFrame, share: float, fund: int) -> pd.DataFrame:
    """Выплаты: доля в десятитысячных, дробная часть рубля отбрасывается."""
    raise NotImplementedError
