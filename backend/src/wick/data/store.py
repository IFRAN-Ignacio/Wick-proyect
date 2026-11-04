"""Almacenamiento de velas en Parquet (zstd), una partición por mes.

Estructura (03_ARQUITECTURA §3, adaptada al MVP en docs/adr/0001):
    <datos>/data/binance/spot/klines_<tf>/<SYMBOL>/<YYYY-MM>.parquet
    <datos>/data/binance/spot/klines_<tf>/<SYMBOL>/_manifest.json
El manifiesto registra por mes: origen, filas, checksum y si el mes está completo.
Un mes completo no se vuelve a bajar.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from wick.config import market_data_dir
from wick.data.integrity import Gap, find_gaps
from wick.data.parsing import OUTPUT_COLUMNS, DataError
from wick.data.sources.base import MonthData
from wick.data.sources.binance import month_bounds_ms
from wick.data.timeframes import interval_ms

MARKET = "spot"
# Las descargas escriben meses en paralelo: el manifiesto se actualiza de a uno.
_manifest_lock = threading.Lock()


def binance_dir() -> Path:
    path = market_data_dir() / "binance"
    path.mkdir(parents=True, exist_ok=True)
    return path


def series_dir(symbol: str, timeframe: str) -> Path:
    return binance_dir() / MARKET / f"klines_{timeframe}" / symbol


def month_key(year: int, month: int) -> str:
    return f"{year:04d}-{month:02d}"


def _manifest_path(symbol: str, timeframe: str) -> Path:
    return series_dir(symbol, timeframe) / "_manifest.json"


def read_manifest(symbol: str, timeframe: str) -> dict[str, dict[str, Any]]:
    path = _manifest_path(symbol, timeframe)
    if not path.exists():
        return {}
    data: dict[str, dict[str, Any]] = json.loads(path.read_text(encoding="utf-8"))
    return data


def _write_json_atomic(path: Path, payload: object) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=1, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)


def is_month_complete(symbol: str, timeframe: str, year: int, month: int) -> bool:
    entry = read_manifest(symbol, timeframe).get(month_key(year, month))
    if not entry or not entry.get("complete"):
        return False
    return (series_dir(symbol, timeframe) / f"{month_key(year, month)}.parquet").exists()


def write_month(symbol: str, timeframe: str, year: int, month: int, data: MonthData) -> None:
    """Escribe la partición de forma atómica (tmp + rename) y actualiza el manifiesto."""
    folder = series_dir(symbol, timeframe)
    folder.mkdir(parents=True, exist_ok=True)
    key = month_key(year, month)
    target = folder / f"{key}.parquet"
    rows_before = len(data.df)
    table = pa.Table.from_pandas(data.df[OUTPUT_COLUMNS], preserve_index=False)
    tmp = target.with_suffix(".parquet.tmp")
    pq.write_table(table, tmp, compression="zstd")
    rows_after = pq.read_metadata(tmp).num_rows
    if rows_after != rows_before:
        tmp.unlink(missing_ok=True)
        raise DataError(f"{symbol} {key}: se escribieron {rows_after} filas de {rows_before}.")
    os.replace(tmp, target)
    with _manifest_lock:
        _update_manifest(symbol, timeframe, key, data, rows_before)


def _update_manifest(
    symbol: str, timeframe: str, key: str, data: MonthData, rows_before: int
) -> None:
    manifest = read_manifest(symbol, timeframe)
    manifest[key] = {
        "source": data.source,
        "complete": data.complete,
        "rows": rows_before,
        "sha256_zip": data.sha256,
        "first_ts": int(data.df["ts"].iloc[0]) if rows_before else None,
        "last_ts": int(data.df["ts"].iloc[-1]) if rows_before else None,
    }
    _write_json_atomic(_manifest_path(symbol, timeframe), manifest)


@dataclass(frozen=True)
class LoadedSeries:
    df: pd.DataFrame
    gaps: list[Gap]
    fingerprint: str


def load_range(symbol: str, timeframe: str, start_ms: int, end_ms: int) -> LoadedSeries:
    """Carga las velas guardadas en [start_ms, end_ms). No rellena huecos: los reporta."""
    folder = series_dir(symbol, timeframe)
    if not folder.exists():
        raise DataError(f"No hay datos descargados de {symbol} {timeframe}.")
    frames: list[pd.DataFrame] = []
    for path in sorted(folder.glob("*.parquet")):
        y, m = (int(x) for x in path.stem.split("-"))
        ms, me = month_bounds_ms(y, m)
        if me <= start_ms or ms >= end_ms:
            continue
        frames.append(pq.read_table(path).to_pandas())
    if not frames:
        raise DataError(f"No hay velas de {symbol} {timeframe} en el rango pedido.")
    df = pd.concat(frames, ignore_index=True)
    df = df[(df["ts"] >= start_ms) & (df["ts"] < end_ms)].reset_index(drop=True)
    if df.empty:
        raise DataError(f"No hay velas de {symbol} {timeframe} en el rango pedido.")
    ts = df["ts"].to_numpy()
    if not bool(np.all(np.diff(ts) > 0)):
        raise DataError(f"{symbol} {timeframe}: timestamps repetidos o desordenados.")
    gaps = find_gaps(ts, interval_ms(timeframe), start_ms, end_ms)
    return LoadedSeries(df=df, gaps=gaps, fingerprint=fingerprint(df))


def fingerprint(df: pd.DataFrame) -> str:
    """Hash de las velas usadas: si los datos cambian, el backtest viejo lo detecta."""
    h = hashlib.sha256()
    for col in ("ts", "open", "high", "low", "close", "volume"):
        h.update(np.ascontiguousarray(df[col].to_numpy()).tobytes())
    return h.hexdigest()[:16]


@dataclass(frozen=True)
class DatasetInfo:
    symbol: str
    timeframe: str
    months: list[str]
    incomplete_months: list[str]
    rows: int
    bytes: int
    first_ts: int | None
    last_ts: int | None
    gaps: list[Gap]
    missing_candles: int


def list_datasets() -> list[DatasetInfo]:
    root = binance_dir() / MARKET
    out: list[DatasetInfo] = []
    if not root.exists():
        return out
    for tf_dir in sorted(root.glob("klines_*")):
        timeframe = tf_dir.name.removeprefix("klines_")
        for sym_dir in sorted(p for p in tf_dir.iterdir() if p.is_dir()):
            files = sorted(sym_dir.glob("*.parquet"))
            if not files:
                continue
            manifest = read_manifest(sym_dir.name, timeframe)
            ts_parts = [pq.read_table(f, columns=["ts"]).column("ts").to_numpy() for f in files]
            ts = np.concatenate(ts_parts) if ts_parts else np.array([], dtype=np.int64)
            gaps = find_gaps(ts, interval_ms(timeframe), None, None) if ts.size else []
            out.append(
                DatasetInfo(
                    symbol=sym_dir.name,
                    timeframe=timeframe,
                    months=[f.stem for f in files],
                    incomplete_months=[
                        f.stem for f in files if not manifest.get(f.stem, {}).get("complete")
                    ],
                    rows=int(ts.size),
                    bytes=sum(f.stat().st_size for f in files),
                    first_ts=int(ts[0]) if ts.size else None,
                    last_ts=int(ts[-1]) if ts.size else None,
                    gaps=gaps,
                    missing_candles=sum(g.missing for g in gaps),
                )
            )
    return out
