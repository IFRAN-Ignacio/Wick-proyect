"""Parseo y validación de velas de Binance.

Trampas que se manejan acá (ver docs/02_STACK.md):
- Algunos CSV traen encabezado y otros no: se detecta mirando la primera fila.
- Desde 2025-01-01 los archivos spot usan microsegundos: se normaliza a ms por
  magnitud, archivo por archivo.
- Nada se "arregla" en silencio: si una validación falla se lanza `DataError`.
"""

from __future__ import annotations

import io
import zipfile

import numpy as np
import numpy.typing as npt
import pandas as pd

KLINE_COLUMNS = 12  # formato de velas de Binance (open_time ... ignore)
OUTPUT_COLUMNS = ["ts", "open", "high", "low", "close", "volume", "trades"]


class DataError(Exception):
    """Dato de Binance inválido o inconsistente. Se reporta, no se rellena."""


def normalize_ts_to_ms(ts: npt.NDArray[np.int64], where: str) -> npt.NDArray[np.int64]:
    """Normaliza timestamps a milisegundos decidiendo por magnitud.

    Supuesto: un archivo entero usa una sola unidad. µs (>1e15) → se divide por 1000;
    ms (>1e12) → se deja igual; cualquier otra magnitud es un error.
    """
    if ts.size == 0:
        return ts
    top = int(ts.max())
    if top > 10**15:
        return ts // 1000
    if top > 10**12:
        return ts
    raise DataError(f"Unidad de timestamp desconocida en {where} (máximo = {top}).")


def _looks_like_header(first_cell: str) -> bool:
    try:
        float(first_cell)
    except ValueError:
        return True
    return False


def parse_kline_csv(raw: bytes, where: str) -> pd.DataFrame:
    """Parsea un CSV de velas (con o sin encabezado) y devuelve las columnas de WICK."""
    text = raw.decode("utf-8")
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return _empty()
    if _looks_like_header(lines[0].split(",")[0].strip()):
        lines = lines[1:]
    if not lines:
        return _empty()
    expected_rows = len(lines)
    df = pd.read_csv(io.StringIO("\n".join(lines)), header=None, dtype=str)
    if df.shape[1] != KLINE_COLUMNS:
        raise DataError(f"{where}: se esperaban {KLINE_COLUMNS} columnas y hay {df.shape[1]}.")
    if len(df) != expected_rows:
        raise DataError(f"{where}: se leyeron {len(df)} filas de {expected_rows}.")
    return rows_to_frame(df.to_numpy(), where)


def rows_to_frame(rows: npt.NDArray[np.object_] | list[list[object]], where: str) -> pd.DataFrame:
    """Convierte filas crudas de velas (CSV o REST) al DataFrame validado."""
    arr = np.asarray(rows, dtype=object)
    if arr.size == 0:
        return _empty()
    if arr.ndim != 2 or arr.shape[1] != KLINE_COLUMNS:
        raise DataError(f"{where}: forma inesperada {arr.shape}.")
    ts = normalize_ts_to_ms(arr[:, 0].astype(np.int64), where)
    df = pd.DataFrame(
        {
            "ts": ts.astype(np.int64),
            "open": arr[:, 1].astype(np.float64),
            "high": arr[:, 2].astype(np.float64),
            "low": arr[:, 3].astype(np.float64),
            "close": arr[:, 4].astype(np.float64),
            "volume": arr[:, 5].astype(np.float64),
            "trades": arr[:, 8].astype(np.int64),
        }
    )
    if len(df) != arr.shape[0]:
        raise DataError(f"{where}: cambió la cantidad de filas al convertir.")
    validate_klines(df, where)
    return df


def validate_klines(df: pd.DataFrame, where: str) -> None:
    """Validaciones OHLC básicas. Cualquier falla es un error explícito."""
    if df.empty:
        return
    ts = df["ts"].to_numpy()
    if not bool(np.all(np.diff(ts) > 0)):
        raise DataError(f"{where}: timestamps no estrictamente crecientes.")
    o, h, low, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    if not bool(np.all(h >= np.maximum(o, c))):
        raise DataError(f"{where}: hay velas con high < max(open, close).")
    if not bool(np.all(low <= np.minimum(o, c))):
        raise DataError(f"{where}: hay velas con low > min(open, close).")
    if not bool(np.all(df["volume"].to_numpy() >= 0)):
        raise DataError(f"{where}: hay volumen negativo.")
    if not bool(np.all(np.isfinite(np.stack([o, h, low, c])))):
        raise DataError(f"{where}: hay precios no finitos.")


def read_single_csv_from_zip(blob: bytes, where: str) -> bytes:
    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        if len(names) != 1:
            raise DataError(f"{where}: el ZIP tiene {len(names)} CSV (se esperaba 1).")
        return zf.read(names[0])


def _empty() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ts": np.array([], dtype=np.int64),
            "open": np.array([], dtype=np.float64),
            "high": np.array([], dtype=np.float64),
            "low": np.array([], dtype=np.float64),
            "close": np.array([], dtype=np.float64),
            "volume": np.array([], dtype=np.float64),
            "trades": np.array([], dtype=np.int64),
        }
    )
