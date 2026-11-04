"""Funciones base compartidas por los indicadores (NumPy + Numba).

Convención: las posiciones sin valor suficiente (warmup) son NaN. Ningún
indicador usa datos posteriores al índice que calcula.
"""

from __future__ import annotations

import numpy as np
import numpy.typing as npt
from numba import njit

F64 = npt.NDArray[np.float64]


def sma(x: F64, n: int) -> F64:
    """Media simple de los últimos `n` valores (incluye el actual)."""
    out = np.full(x.size, np.nan)
    if n < 1 or x.size < n:
        return out
    csum = np.cumsum(np.insert(x, 0, 0.0))
    out[n - 1 :] = (csum[n:] - csum[:-n]) / n
    return out


@njit(cache=True)
def _seeded_recursive(x: F64, n: int, alpha: float) -> F64:  # pragma: no cover - numba
    out = np.full(x.size, np.nan)
    # Arranca en el primer índice con `n` valores válidos consecutivos.
    start = -1
    count = 0
    for i in range(x.size):
        if np.isnan(x[i]):
            count = 0
        else:
            count += 1
            if count == n:
                start = i
                break
    if start < 0:
        return out
    acc = 0.0
    for k in range(start - n + 1, start + 1):
        acc += x[k]
    prev = acc / n
    out[start] = prev
    for i in range(start + 1, x.size):
        prev = alpha * x[i] + (1.0 - alpha) * prev
        out[i] = prev
    return out


def ema(x: F64, n: int) -> F64:
    """EMA con alpha = 2/(n+1), sembrada con la SMA de los primeros `n` valores."""
    return np.asarray(_seeded_recursive(x, n, 2.0 / (n + 1)), dtype=np.float64)


def rma(x: F64, n: int) -> F64:
    """Media de Wilder (alpha = 1/n), sembrada con la SMA de los primeros `n` valores."""
    return np.asarray(_seeded_recursive(x, n, 1.0 / n), dtype=np.float64)
