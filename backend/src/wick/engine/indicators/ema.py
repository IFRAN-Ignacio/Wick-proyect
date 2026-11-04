"""EMA: alpha = 2/(length+1), primer valor = SMA de las primeras `length` velas."""

from __future__ import annotations

from wick.engine.indicators._common import F64, ema


def compute(src: F64, length: int) -> F64:
    return ema(src, length)
