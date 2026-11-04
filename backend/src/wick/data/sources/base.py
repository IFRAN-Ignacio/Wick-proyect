"""Interfaz `DataSource`: la única preparación permitida para otros exchanges.

En v1 hay una sola implementación (`BinanceSource`).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import pandas as pd


@dataclass(frozen=True)
class SymbolInfo:
    symbol: str
    status: str
    base_asset: str
    quote_asset: str
    step_size: float
    tick_size: float
    min_notional: float


@dataclass(frozen=True)
class MonthData:
    """Velas de un mes calendario UTC, ya normalizadas y validadas."""

    df: pd.DataFrame
    source: str  # "monthly_zip" | "rest"
    complete: bool  # False si el mes todavía no terminó
    sha256: str | None


class DataSource(Protocol):
    def fetch_symbols(self) -> list[SymbolInfo]: ...

    def fetch_month(self, symbol: str, timeframe: str, year: int, month: int) -> MonthData: ...
