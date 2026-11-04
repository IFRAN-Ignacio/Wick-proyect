"""Indicadores contra valores calculados a mano (series SINTÉTICAS chicas)."""

from __future__ import annotations

import math

import numpy as np
import pytest

from wick.engine import indicators

nan = math.nan


def _c(values: list[float]) -> dict[str, np.ndarray]:
    a = np.array(values, dtype=np.float64)
    return {"open": a, "high": a, "low": a, "close": a}


def assert_series(got: np.ndarray, expected: list[float]) -> None:
    assert got.shape == (len(expected),)
    for g, e in zip(got, expected, strict=True):
        if math.isnan(e):
            assert math.isnan(g)
        else:
            assert g == pytest.approx(e, rel=1e-12, abs=1e-12)


def test_sma() -> None:
    out = indicators.compute("sma", {"length": 3}, _c([1, 2, 3, 4, 5]))[""]
    assert_series(out, [nan, nan, 2, 3, 4])


def test_ema_sembrada_con_sma() -> None:
    # alpha = 2/(3+1) = 0.5; semilla = (1+2+3)/3 = 2; luego 0.5·x + 0.5·prev
    out = indicators.compute("ema", {"length": 3}, _c([1, 2, 3, 4, 5, 6]))[""]
    assert_series(out, [nan, nan, 2, 3, 4, 5])


def test_rsi_wilder() -> None:
    # cambios: +1 +1 −1 +1 · Wilder n=2 (alpha 0.5)
    # gan: 1, 0.5, 0.75 · pér: 0, 0.5, 0.25 → RSI 100, 50, 75
    out = indicators.compute("rsi", {"length": 2}, _c([1, 2, 3, 2, 3]))[""]
    assert_series(out, [nan, nan, 100, 50, 75])


def test_macd() -> None:
    x = [1, 2, 4, 8, 16]
    out = indicators.compute("macd", {"fast": 2, "slow": 3, "signal": 2}, _c(x))
    a2 = 2 / 3  # alpha de EMA(2)
    f1 = 1.5
    f2 = a2 * 4 + (1 - a2) * f1
    f3 = a2 * 8 + (1 - a2) * f2
    f4 = a2 * 16 + (1 - a2) * f3
    s2 = 7 / 3
    s3 = 0.5 * 8 + 0.5 * s2
    s4 = 0.5 * 16 + 0.5 * s3
    m = [nan, nan, f2 - s2, f3 - s3, f4 - s4]
    sig3 = (m[2] + m[3]) / 2
    sig4 = a2 * m[4] + (1 - a2) * sig3
    assert_series(out["macd"], m)
    assert_series(out["signal"], [nan, nan, nan, sig3, sig4])
    assert_series(out["hist"], [nan, nan, nan, m[3] - sig3, m[4] - sig4])
    assert out["macd"][2] == pytest.approx(5 / 6)


def test_bollinger_desvio_poblacional() -> None:
    out = indicators.compute("bbands", {"length": 3, "mult": 2}, _c([1, 2, 3, 4]))
    sd = math.sqrt(2 / 3)
    assert_series(out["middle"], [nan, nan, 2, 3])
    assert_series(out["upper"], [nan, nan, 2 + 2 * sd, 3 + 2 * sd])
    assert_series(out["lower"], [nan, nan, 2 - 2 * sd, 3 - 2 * sd])


def test_bollinger_precision_con_precios_grandes() -> None:
    x = [100000.0, 100001.0, 100002.0]
    out = indicators.compute("bbands", {"length": 3, "mult": 1}, _c(x))
    assert out["upper"][2] - out["middle"][2] == pytest.approx(math.sqrt(2 / 3), rel=1e-9)


def test_atr_wilder() -> None:
    ohlc = {
        "open": np.array([9.0, 9.0, 11.0]),
        "high": np.array([10.0, 12.0, 11.0]),
        "low": np.array([8.0, 9.0, 7.0]),
        "close": np.array([9.0, 11.0, 8.0]),
    }
    # TR: 2, max(3, 3, 0)=3, max(4, 0, 4)=4 · ATR(2): (2+3)/2 = 2.5; 0.5·4 + 0.5·2.5 = 3.25
    out = indicators.compute("atr", {"length": 2}, ohlc)[""]
    assert_series(out, [nan, 2.5, 3.25])


def test_largo_no_entero_es_error() -> None:
    with pytest.raises(ValueError):
        indicators.compute("ema", {"length": 2.5}, _c([1, 2, 3]))
