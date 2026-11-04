"""MACD: EMA(fast) − EMA(slow); señal = EMA(signal) del MACD; histograma = MACD − señal."""

from __future__ import annotations

from wick.engine.indicators._common import F64, ema


def compute(src: F64, fast: int, slow: int, signal: int) -> dict[str, F64]:
    line = ema(src, fast) - ema(src, slow)
    sig = ema(line, signal)
    return {"macd": line, "signal": sig, "hist": line - sig}
