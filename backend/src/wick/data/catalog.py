"""Catálogo de símbolos spot, cacheado en `binance/catalog.json` con fecha de captura."""

from __future__ import annotations

import json
import os
import time
from dataclasses import asdict
from typing import Any

from wick.data.sources.base import DataSource, SymbolInfo
from wick.data.store import binance_dir

MAX_AGE_S = 24 * 3600


def _path() -> Any:
    return binance_dir() / "catalog.json"


def load_catalog(source: DataSource, refresh: bool = False) -> tuple[list[SymbolInfo], int]:
    """Devuelve (símbolos, fetched_at_ms). Usa la caché si tiene menos de un día."""
    path = _path()
    if path.exists() and not refresh:
        data = json.loads(path.read_text(encoding="utf-8"))
        fetched_at = int(data["fetched_at"])
        if time.time() * 1000 - fetched_at < MAX_AGE_S * 1000:
            return [SymbolInfo(**s) for s in data["symbols"]], fetched_at
    symbols = source.fetch_symbols()
    fetched_at = int(time.time() * 1000)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps({"fetched_at": fetched_at, "symbols": [asdict(s) for s in symbols]}),
        encoding="utf-8",
    )
    os.replace(tmp, path)
    return symbols, fetched_at


def search(symbols: list[SymbolInfo], query: str, limit: int = 50) -> list[SymbolInfo]:
    q = query.strip().upper()
    if not q:
        hits = symbols
    else:
        hits = [s for s in symbols if q in s.symbol]
        hits.sort(key=lambda s: (not s.symbol.startswith(q), s.status != "TRADING", s.symbol))
    return hits[:limit]


def find_symbol(source: DataSource, symbol: str) -> SymbolInfo | None:
    symbols, _ = load_catalog(source)
    for s in symbols:
        if s.symbol == symbol:
            return s
    return None
