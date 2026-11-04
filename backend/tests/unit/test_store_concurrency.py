"""Regresión: varios hilos escribiendo meses del mismo símbolo no pierden entradas del manifiesto."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd

from wick.data import store
from wick.data.sources.base import MonthData
from wick.data.sources.binance import month_bounds_ms


def _month(y: int, m: int) -> MonthData:
    start, end = month_bounds_ms(y, m)
    ts = np.arange(start, end, 86_400_000, dtype=np.int64)
    one = np.ones(ts.size)
    df = pd.DataFrame(  # SINTÉTICO
        {
            "ts": ts,
            "open": one,
            "high": one,
            "low": one,
            "close": one,
            "volume": one,
            "trades": np.ones(ts.size, dtype=np.int64),
        }
    )
    return MonthData(df=df, source="synthetic", complete=True, sha256=None)


def test_escrituras_en_paralelo_no_pierden_meses() -> None:
    months = [(2022, m) for m in range(1, 13)]
    with ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(lambda ym: store.write_month("CONCURUSDT", "1d", *ym, _month(*ym)), months))
    manifest = store.read_manifest("CONCURUSDT", "1d")
    assert sorted(manifest) == [f"2022-{m:02d}" for m in range(1, 13)]
    assert all(store.is_month_complete("CONCURUSDT", "1d", y, m) for y, m in months)
