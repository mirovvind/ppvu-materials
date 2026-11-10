"""Тесты распределения фонда премирования (заготовка)."""

import numpy as np
import pytest

from src.fund import best_share


def test_best_share_fund_short() -> None:
    share = best_share(np.array([50000, 50000]), fund=60000)
    assert share == pytest.approx(0.6)
