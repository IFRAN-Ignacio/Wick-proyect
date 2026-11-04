"""RSI de Wilder.

Supuestos: ganancias/pérdidas promediadas con la media de Wilder sembrada con la
media simple de los primeros `length` cambios. Si la pérdida media es 0: RSI = 100
(o 50 si la ganancia media también es 0).
"""

from __future__ import annotations

import numpy as np

from wick.engine.indicators._common import F64, rma


def compute(src: F64, length: int) -> F64:
    out = np.full(src.size, np.nan)
    if src.size <= length:
        return out
    delta = np.diff(src)
    gains = np.where(delta > 0, delta, 0.0)
    losses = np.where(delta < 0, -delta, 0.0)
    avg_g = rma(gains, length)
    avg_l = rma(losses, length)
    with np.errstate(divide="ignore", invalid="ignore"):
        rs = avg_g / avg_l
        val = 100.0 - 100.0 / (1.0 + rs)
    val = np.where(avg_l == 0, np.where(avg_g == 0, 50.0, 100.0), val)
    val = np.where(np.isnan(avg_g) | np.isnan(avg_l), np.nan, val)
    out[1:] = val
    return out
