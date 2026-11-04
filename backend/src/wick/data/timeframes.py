"""Timeframes soportados en el MVP y su duración en milisegundos."""

from __future__ import annotations

from typing import Literal, get_args

Timeframe = Literal["1m", "5m", "15m", "1h", "4h", "1d"]

TIMEFRAMES: tuple[str, ...] = get_args(Timeframe)

_MINUTE = 60_000

INTERVAL_MS: dict[str, int] = {
    "1m": _MINUTE,
    "5m": 5 * _MINUTE,
    "15m": 15 * _MINUTE,
    "1h": 60 * _MINUTE,
    "4h": 240 * _MINUTE,
    "1d": 1440 * _MINUTE,
}


def interval_ms(tf: str) -> int:
    if tf not in INTERVAL_MS:
        raise ValueError(f"Timeframe no soportado: {tf}")
    return INTERVAL_MS[tf]
