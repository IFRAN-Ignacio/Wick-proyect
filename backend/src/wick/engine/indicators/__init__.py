"""Registro de indicadores del MVP: SMA, EMA, RSI, MACD, Bollinger y ATR."""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np

from wick.engine.indicators import atr, bbands, ema, macd, rsi, sma
from wick.engine.indicators._common import F64


def _int_param(params: Mapping[str, float], name: str) -> int:
    v = params[name]
    if float(v) != int(v) or int(v) < 1:
        raise ValueError(f"El parámetro '{name}' tiene que ser un entero mayor o igual a 1 ({v}).")
    return int(v)


def compute(
    kind: str,
    params: Mapping[str, float],
    ohlc: Mapping[str, F64],
    source: str = "close",
) -> dict[str, F64]:
    """Calcula un indicador. Devuelve sus series de salida ("" = serie principal)."""
    src = np.ascontiguousarray(ohlc[source], dtype=np.float64)
    if kind == "sma":
        return {"": sma.compute(src, _int_param(params, "length"))}
    if kind == "ema":
        return {"": ema.compute(src, _int_param(params, "length"))}
    if kind == "rsi":
        return {"": rsi.compute(src, _int_param(params, "length"))}
    if kind == "macd":
        return macd.compute(
            src,
            _int_param(params, "fast"),
            _int_param(params, "slow"),
            _int_param(params, "signal"),
        )
    if kind == "bbands":
        return bbands.compute(src, _int_param(params, "length"), float(params["mult"]))
    if kind == "atr":
        return {
            "": atr.compute(
                np.ascontiguousarray(ohlc["high"], dtype=np.float64),
                np.ascontiguousarray(ohlc["low"], dtype=np.float64),
                np.ascontiguousarray(ohlc["close"], dtype=np.float64),
                _int_param(params, "length"),
            )
        }
    raise ValueError(f"Indicador desconocido: {kind}")
