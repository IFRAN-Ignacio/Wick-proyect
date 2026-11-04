"""Métricas de un backtest. Todo sale de la curva de equity y de los trades.

Nunca se usa un capital hardcodeado: el punto de partida es el capital inicial
de la corrida, que es el primer punto de la curva.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import numpy.typing as npt

F64 = npt.NDArray[np.float64]
I64 = npt.NDArray[np.int64]
DAY_MS = 86_400_000


def max_drawdown(curve: F64) -> float:
    """Máxima caída desde un máximo previo, como fracción positiva (0.25 = −25%)."""
    peak = np.maximum.accumulate(curve)
    return float(np.max(1.0 - curve / peak)) if curve.size else 0.0


def daily_returns(ts: I64, equity: F64, start_equity: float) -> F64:
    """Retornos diarios UTC usando el último valor de equity de cada día."""
    days = ts // DAY_MS
    last_idx = np.nonzero(np.diff(days, append=days[-1] + 1))[0]
    daily = np.concatenate([[start_equity], equity[last_idx]])
    return np.asarray(daily[1:] / daily[:-1] - 1.0, dtype=np.float64)


def sharpe_daily(ts: I64, equity: F64, start_equity: float) -> float | None:
    """Sharpe con retornos diarios, rf = 0, anualizado × √365 (cripto opera todos los días)."""
    r = daily_returns(ts, equity, start_equity)
    if r.size < 2:
        return None
    sd = float(np.std(r, ddof=1))
    if sd == 0.0 or not math.isfinite(sd):
        return None
    return float(np.mean(r) / sd * math.sqrt(365.0))


def buy_and_hold(open_first: float, close_last: float, taker: float, slippage: float) -> float:
    """Comprar en el open de la primera vela y vender al close de la última, con los mismos costos."""
    buy = open_first * (1.0 + slippage) * (1.0 + taker)
    sell = close_last * (1.0 - slippage) * (1.0 - taker)
    return sell / buy - 1.0


def compute_metrics(
    ts: I64,
    equity: F64,
    start_equity: float,
    pnl_net: F64,
    fees: F64,
    n_ambiguous: int,
    n_skipped: int,
    bh_return: float,
    bars_in_position: int,
) -> dict[str, Any]:
    curve = np.concatenate([[start_equity], equity])
    n = int(pnl_net.size)
    wins = pnl_net[pnl_net > 0]
    losses = pnl_net[pnl_net < 0]
    gross_win = float(wins.sum())
    gross_loss = float(-losses.sum())
    if n == 0:
        profit_factor: float | None = None
        win_rate: float | None = None
    else:
        win_rate = float(wins.size / n)
        profit_factor = gross_win / gross_loss if gross_loss > 0 else None
    return {
        "total_return": float(curve[-1] / curve[0] - 1.0),
        "final_equity": float(curve[-1]),
        "max_dd": max_drawdown(curve),
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "profit_factor_infinite": bool(n > 0 and gross_loss == 0 and gross_win > 0),
        "n_trades": n,
        "n_wins": int(wins.size),
        "n_losses": int(losses.size),
        "sharpe": sharpe_daily(ts, equity, start_equity),
        "fees_paid": float(fees.sum()),
        "n_ambiguous": int(n_ambiguous),
        "n_skipped_min_notional": int(n_skipped),
        "buy_hold_return": float(bh_return),
        "exposure": float(bars_in_position / equity.size) if equity.size else 0.0,
        "net_pnl": float(pnl_net.sum()),
    }
