"""Desglose mensual (UTC): retorno de la equity y trades cerrados en cada mes."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import numpy as np
import numpy.typing as npt

F64 = npt.NDArray[np.float64]
I64 = npt.NDArray[np.int64]


def _month_key(ts_ms: int) -> str:
    d = datetime.fromtimestamp(ts_ms / 1000, tz=UTC)
    return f"{d.year:04d}-{d.month:02d}"


def monthly(
    ts: I64,
    equity: F64,
    start_equity: float,
    exit_ts: I64,
    pnl_net: F64,
) -> list[dict[str, Any]]:
    """Retorno del mes = equity al cierre del mes / equity al cierre del mes anterior − 1.

    Los trades se asignan al mes en que se CERRARON.
    """
    keys = [_month_key(int(t)) for t in ts]
    trade_keys = [_month_key(int(t)) for t in exit_ts]
    out: list[dict[str, Any]] = []
    prev = start_equity
    i = 0
    n = len(keys)
    while i < n:
        k = keys[i]
        j = i
        while j + 1 < n and keys[j + 1] == k:
            j += 1
        end_eq = float(equity[j])
        mask = np.array([tk == k for tk in trade_keys], dtype=np.bool_)
        month_pnl = pnl_net[mask] if mask.size else np.array([], dtype=np.float64)
        out.append(
            {
                "month": k,
                "return": end_eq / prev - 1.0,
                "start_equity": prev,
                "end_equity": end_eq,
                "n_trades": int(month_pnl.size),
                "net_pnl": float(month_pnl.sum()),
                "n_wins": int((month_pnl > 0).sum()),
            }
        )
        prev = end_eq
        i = j + 1
    return out
