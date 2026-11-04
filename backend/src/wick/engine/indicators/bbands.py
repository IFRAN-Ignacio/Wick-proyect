"""Bandas de Bollinger: media = SMA(length); bandas = media ± mult × desvío poblacional (ddof=0)."""

from __future__ import annotations

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

from wick.engine.indicators._common import F64, sma


def compute(src: F64, length: int, mult: float) -> dict[str, F64]:
    mid = sma(src, length)
    sd = np.full(src.size, np.nan)
    if src.size >= length:
        # Desvío por ventana (no E[x²]−E[x]², que pierde precisión con precios grandes).
        sd[length - 1 :] = sliding_window_view(src, length).std(axis=1)
    return {"upper": mid + mult * sd, "middle": mid, "lower": mid - mult * sd}
