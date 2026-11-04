"""Corrida de UNA variante concreta: indicadores → señales → núcleo → métricas.

Recibe arrays (no lee disco ni red). `IndicatorCache` evita recalcular el mismo
indicador cuando varias variantes lo comparten.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import numpy as np
import numpy.typing as npt

from wick.engine import breakdown, core, indicators, metrics, signals
from wick.engine.indicators._common import F64

I64 = npt.NDArray[np.int64]


@dataclass(frozen=True)
class Market:
    """Velas del timeframe de la estrategia, ya filtradas al rango."""

    ts: I64
    open: F64
    high: F64
    low: F64
    close: F64
    step_size: float
    min_notional: float

    def ohlc(self) -> dict[str, F64]:
        return {"open": self.open, "high": self.high, "low": self.low, "close": self.close}


class IndicatorCache:
    def __init__(self, market: Market) -> None:
        self._market = market
        self._ohlc = market.ohlc()
        self._cache: dict[str, dict[str, F64]] = {}

    def get(self, kind: str, params: dict[str, float], source: str) -> dict[str, F64]:
        key = json.dumps([kind, sorted(params.items()), source])
        if key not in self._cache:
            self._cache[key] = indicators.compute(kind, params, self._ohlc, source)
        return self._cache[key]


def _series(cfg: dict[str, Any], cache: IndicatorCache, market: Market) -> dict[str, F64]:
    out: dict[str, F64] = dict(market.ohlc())
    for ind in cfg["indicators"]:
        params = {k: float(v) for k, v in ind["params"].items()}
        for name, arr in cache.get(ind["type"], params, ind["source"]).items():
            out[ind["id"] if name == "" else f"{ind['id']}.{name}"] = arr
    return out


def _conditions(rule: dict[str, Any] | None) -> list[tuple[str, str, str | float]] | None:
    if rule is None:
        return None
    conds: list[tuple[str, str, str | float]] = []
    for c in rule["conditions"]:
        right = c["right"] if isinstance(c["right"], str) else float(c["right"]["value"])
        conds.append((c["left"], c["op"], right))
    return conds


@dataclass(frozen=True)
class RunResult:
    metrics: dict[str, Any]
    equity: F64
    trades: npt.NDArray[np.float64]
    entry_signal: npt.NDArray[np.bool_]


def run(cfg: dict[str, Any], market: Market, cache: IndicatorCache | None = None) -> RunResult:
    """Corre una variante concreta (todos los parámetros escalares)."""
    cache = cache or IndicatorCache(market)
    n = market.ts.size
    if n < 2:
        raise ValueError("Hacen falta al menos 2 velas para simular.")
    series = _series(cfg, cache, market)
    long_conds = _conditions(cfg["entry"]["long"])
    assert long_conds is not None
    entry = signals.rule_signal(long_conds, series, n)
    short_conds = _conditions(cfg["entry"].get("short"))
    exit_sig = (
        signals.rule_signal(short_conds, series, n)
        if short_conds is not None
        else np.zeros(n, dtype=np.bool_)
    )

    stop = cfg["exit"]["stop"]
    tp = cfg["exit"]["take_profit"]
    stop_type = {"none": core.STOP_NONE, "pct": core.STOP_PCT, "atr": core.STOP_ATR}[stop["type"]]
    tp_type = {"none": core.TP_NONE, "pct": core.TP_PCT, "rr": core.TP_RR}[tp["type"]]
    if stop_type == core.STOP_ATR:
        atr = cache.get("atr", {"length": float(stop["atr_length"])}, "close")[""]
        # Sin ATR todavía (warmup) no hay stop calculable: no se entra.
        entry = entry & ~np.isnan(atr)
    else:
        atr = np.full(n, np.nan)

    costs = cfg["costs"]
    equity, trades, counters = core.simulate(
        market.open,
        market.high,
        market.low,
        market.close,
        entry,
        exit_sig,
        atr,
        float(cfg["capital"]),
        float(cfg["sizing"]["value"]) / 100.0,
        bool(cfg["sizing"]["compound"]),
        float(costs["taker"]),
        float(costs["slippage"]),
        stop_type,
        float(stop["pct"]) / 100.0,
        float(stop["mult"]),
        tp_type,
        float(tp["pct"]) / 100.0,
        float(tp["ratio"]),
        bool(cfg["exit"]["on_opposite_signal"]),
        market.step_size,
        market.min_notional,
    )
    pnl = trades[:, 7]
    fees = trades[:, 5] + trades[:, 6]
    bars_in = int(np.sum(trades[:, 1] - trades[:, 0] + 1)) if trades.size else 0
    m = metrics.compute_metrics(
        market.ts,
        equity,
        float(cfg["capital"]),
        pnl,
        fees,
        int(counters[0]),
        int(counters[1]),
        metrics.buy_and_hold(
            float(market.open[0]),
            float(market.close[-1]),
            float(costs["taker"]),
            float(costs["slippage"]),
        ),
        bars_in,
    )
    return RunResult(metrics=m, equity=equity, trades=trades, entry_signal=entry)


def trades_table(result: RunResult, market: Market) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in result.trades:
        ei, xi, si = int(row[0]), int(row[1]), int(row[10])
        cost = row[2] * row[4] + row[5]
        out.append(
            {
                "signal_ts": int(market.ts[si]),
                "entry_ts": int(market.ts[ei]),
                "exit_ts": int(market.ts[xi]),
                "entry_price": float(row[2]),
                "exit_price": float(row[3]),
                "qty": float(row[4]),
                "fees": float(row[5] + row[6]),
                "pnl_net": float(row[7]),
                "return_pct": float(row[7] / cost) if cost > 0 else 0.0,
                "reason": core.EXIT_REASONS[int(row[8])],
                "ambiguous": bool(row[9]),
            }
        )
    return out


def monthly_breakdown(result: RunResult, market: Market, capital: float) -> list[dict[str, Any]]:
    exit_ts = (
        market.ts[result.trades[:, 1].astype(np.int64)]
        if result.trades.size
        else np.array([], dtype=np.int64)
    )
    pnl = result.trades[:, 7] if result.trades.size else np.array([], dtype=np.float64)
    return breakdown.monthly(market.ts, result.equity, capital, exit_ts, pnl)
