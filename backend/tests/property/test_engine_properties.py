"""Invariantes del motor con velas SINTÉTICAS aleatorias (random walk, semilla fija).

- Conservación del dinero: equity_final = capital + Σ pnl_bruto − Σ fees.
- Sin look-ahead: alterar las velas posteriores a t no cambia ninguna decisión <= t.
- Costos cero: comprar y mantener coincide exactamente con el retorno del precio.
"""

from __future__ import annotations

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from wick.engine import backtest
from wick.engine.backtest import Market


def synthetic_market(seed: int, n: int = 400) -> Market:
    """Random walk SINTÉTICO, solo para tests."""
    rng = np.random.default_rng(seed)
    close = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, n)))
    open_ = np.concatenate([[100.0], close[:-1]]) * (1 + rng.normal(0, 0.002, n))
    high = np.maximum(open_, close) * (1 + np.abs(rng.normal(0, 0.005, n)))
    low = np.minimum(open_, close) * (1 - np.abs(rng.normal(0, 0.005, n)))
    ts = (np.arange(n, dtype=np.int64) * 3_600_000) + 1_700_000_000_000
    return Market(
        ts=ts, open=open_, high=high, low=low, close=close, step_size=0.0, min_notional=0.0
    )


def ema_cross_cfg(stop: float = 2.0, tp: float = 4.0, size: float = 50.0) -> dict:
    return {
        "capital": 1000.0,
        "indicators": [
            {"id": "f", "type": "ema", "params": {"length": 5.0}, "source": "close"},
            {"id": "s", "type": "ema", "params": {"length": 20.0}, "source": "close"},
            {"id": "atr", "type": "atr", "params": {"length": 14.0}, "source": "close"},
        ],
        "entry": {
            "long": {"conditions": [{"left": "f", "op": "crosses_above", "right": "s"}]},
            "short": {"conditions": [{"left": "f", "op": "crosses_below", "right": "s"}]},
        },
        "exit": {
            "stop": {"type": "pct", "pct": stop, "atr_length": 14.0, "mult": 2.0},
            "take_profit": {"type": "pct", "pct": tp, "ratio": 2.0},
            "on_opposite_signal": True,
        },
        "sizing": {"mode": "pct_capital", "value": size, "compound": True},
        "costs": {"taker": 0.001, "slippage": 0.0005},
    }


@settings(max_examples=25, deadline=None)
@given(
    seed=st.integers(0, 10_000),
    stop=st.sampled_from([1.0, 2.0, 5.0]),
    size=st.sampled_from([10.0, 50.0, 100.0]),
)
def test_conservacion_del_dinero(seed: int, stop: float, size: float) -> None:
    m = synthetic_market(seed)
    r = backtest.run(ema_cross_cfg(stop=stop, size=size), m)
    t = r.trades
    gross = float(np.sum((t[:, 3] - t[:, 2]) * t[:, 4]))
    fees = float(np.sum(t[:, 5] + t[:, 6]))
    assert r.equity[-1] == pytest.approx(1000.0 + gross - fees, abs=1e-6)
    assert r.metrics["final_equity"] == pytest.approx(1000.0 + float(np.sum(t[:, 7])), abs=1e-6)
    assert r.metrics["fees_paid"] == pytest.approx(fees)


@settings(max_examples=25, deadline=None)
@given(seed=st.integers(0, 10_000), cut=st.integers(50, 350))
def test_sin_look_ahead(seed: int, cut: int) -> None:
    m = synthetic_market(seed)
    base = backtest.run(ema_cross_cfg(), m)
    # Se reemplaza TODO lo posterior a `cut` por otro random walk.
    other = synthetic_market(seed + 99_999)
    scale = m.close[cut] / other.open[cut + 1]

    def splice(a: np.ndarray, b: np.ndarray) -> np.ndarray:
        out = a.copy()
        out[cut + 1 :] = b[cut + 1 :] * scale
        return out

    m2 = Market(
        ts=m.ts,
        open=splice(m.open, other.open),
        high=splice(m.high, other.high),
        low=splice(m.low, other.low),
        close=splice(m.close, other.close),
        step_size=0.0,
        min_notional=0.0,
    )
    alt = backtest.run(ema_cross_cfg(), m2)
    # Señales hasta cut: idénticas.
    assert np.array_equal(base.entry_signal[: cut + 1], alt.entry_signal[: cut + 1])
    # Equity hasta cut: idéntica.
    assert np.array_equal(base.equity[: cut + 1], alt.equity[: cut + 1])
    # Trades cerrados antes de cut: idénticos (las entradas en cut+1 usan el open de cut+1,
    # que sí cambió, así que solo se comparan los trades con salida <= cut).
    tb = base.trades[base.trades[:, 1] <= cut]
    ta = alt.trades[alt.trades[:, 1] <= cut]
    # El último trade de `base` podría cerrarse por fin de período: no aplica porque cut < n-1.
    assert np.array_equal(tb, ta)


def test_costos_cero_comprar_y_mantener_coincide_con_el_precio() -> None:
    m = synthetic_market(7)
    cfg = {
        "capital": 1000.0,
        "indicators": [],
        "entry": {"long": {"conditions": [{"left": "close", "op": ">", "right": {"value": 0.0}}]}},
        "exit": {
            "stop": {"type": "none", "pct": 2.0, "atr_length": 14.0, "mult": 2.0},
            "take_profit": {"type": "none", "pct": 4.0, "ratio": 2.0},
            "on_opposite_signal": False,
        },
        "sizing": {"mode": "pct_capital", "value": 100.0, "compound": True},
        "costs": {"taker": 0.0, "slippage": 0.0},
    }
    r = backtest.run(cfg, m)
    assert r.trades.shape[0] == 1
    expected = m.close[-1] / m.open[1] - 1.0  # entra en el open de la vela 1
    assert r.metrics["total_return"] == pytest.approx(expected, rel=1e-12)


def test_determinismo() -> None:
    m = synthetic_market(3)
    a = backtest.run(ema_cross_cfg(), m)
    b = backtest.run(ema_cross_cfg(), m)
    assert a.equity.tobytes() == b.equity.tobytes()
    assert a.trades.tobytes() == b.trades.tobytes()
