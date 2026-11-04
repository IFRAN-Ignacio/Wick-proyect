"""SMA: media simple de `length` velas."""

from __future__ import annotations

from wick.engine.indicators._common import F64, sma


def compute(src: F64, length: int) -> F64:
    return sma(src, length)
