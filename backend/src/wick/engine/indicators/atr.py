"""ATR de Wilder.

TR[0] = high − low; TR[i] = max(high − low, |high − close[i−1]|, |low − close[i−1]|).
ATR = media de Wilder del TR, sembrada con la SMA de los primeros `length` TR.
"""

from __future__ import annotations

import numpy as np

from wick.engine.indicators._common import F64, rma


def true_range(high: F64, low: F64, close: F64) -> F64:
    tr = high - low
    prev = close[:-1]
    tr[1:] = np.maximum.reduce([tr[1:], np.abs(high[1:] - prev), np.abs(low[1:] - prev)])
    return tr


def compute(high: F64, low: F64, close: F64, length: int) -> F64:
    return rma(true_range(high, low, close), length)
