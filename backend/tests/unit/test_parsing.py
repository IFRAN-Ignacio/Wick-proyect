"""Parseo de CSV de Binance con muestras REALES chicas (tests/fixtures/real)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from wick.data.integrity import find_gaps
from wick.data.parsing import DataError, normalize_ts_to_ms, parse_kline_csv

REAL = Path(__file__).resolve().parents[1] / "fixtures" / "real"
HEADER = (
    "open_time,open,high,low,close,volume,close_time,quote_volume,count,"
    "taker_buy_volume,taker_buy_quote_volume,ignore"
)


def _read(name: str) -> bytes:
    return (REAL / name).read_bytes()


def test_2024_12_en_milisegundos() -> None:
    df = parse_kline_csv(_read("BTCUSDT-1h-2024-12.head5.csv"), "2024-12")
    assert len(df) == 5
    assert int(df["ts"].iloc[0]) == 1733011200000  # 2024-12-01 00:00 UTC
    assert df["open"].iloc[0] == pytest.approx(96407.99)
    assert df["trades"].iloc[0] == 154693


def test_2025_01_en_microsegundos_se_normaliza_a_ms() -> None:
    raw = _read("BTCUSDT-1h-2025-01.head5.csv")
    assert raw.startswith(b"1735689600000000")  # el archivo real viene en µs
    df = parse_kline_csv(raw, "2025-01")
    assert int(df["ts"].iloc[0]) == 1735689600000  # 2025-01-01 00:00 UTC en ms
    assert np.all(np.diff(df["ts"].to_numpy()) == 3_600_000)


def test_limite_2024_12_a_2025_01_queda_continuo_en_ms() -> None:
    dec = parse_kline_csv(_read("BTCUSDT-1h-2024-12.head5.csv"), "dec")
    jan = parse_kline_csv(_read("BTCUSDT-1h-2025-01.head5.csv"), "jan")
    assert dec["ts"].max() < jan["ts"].min()
    assert jan["ts"].min() - dec["ts"].max() < 40 * 86_400_000  # mismo orden de magnitud


def test_csv_con_encabezado_se_detecta() -> None:
    raw = (HEADER + "\n").encode() + _read("BTCUSDT-1h-2024-12.head5.csv")
    df = parse_kline_csv(raw, "con encabezado")
    assert len(df) == 5
    assert int(df["ts"].iloc[0]) == 1733011200000


def test_columnas_de_mas_es_error() -> None:
    raw = b"\n".join(line + b",extra" for line in _read("BTCUSDT-1h-2024-12.head5.csv").splitlines())
    with pytest.raises(DataError):
        parse_kline_csv(raw, "13 columnas")


def test_unidad_desconocida_es_error() -> None:
    with pytest.raises(DataError):
        normalize_ts_to_ms(np.array([1_700_000_000], dtype=np.int64), "segundos")


def test_huecos_se_reportan() -> None:
    step = 3_600_000
    ts = np.array([0, step, 4 * step, 5 * step], dtype=np.int64)
    gaps = find_gaps(ts, step, None, None)
    assert len(gaps) == 1
    assert gaps[0].from_ts == 2 * step and gaps[0].to_ts == 3 * step and gaps[0].missing == 2
