"""Flujo API → datos guardados → motor → resultado, con velas SINTÉTICAS en un directorio temporal.

No usa internet: el catálogo y las velas se escriben a mano en la carpeta temporal de tests.
"""

from __future__ import annotations

import json
import time

import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from wick.data import store
from wick.data.sources.base import MonthData
from wick.data.sources.binance import month_bounds_ms
from wick.main import app

SYM = "SYNTHUSDT"  # símbolo SINTÉTICO de test


def _write_synthetic_month(y: int, m: int, seed: int) -> None:
    start, end = month_bounds_ms(y, m)
    ts = np.arange(start, end, 3_600_000, dtype=np.int64)
    rng = np.random.default_rng(seed)
    close = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, ts.size)))
    open_ = np.concatenate([[close[0]], close[:-1]])
    df = pd.DataFrame(
        {
            "ts": ts,
            "open": open_,
            "high": np.maximum(open_, close) * 1.003,
            "low": np.minimum(open_, close) * 0.997,
            "close": close,
            "volume": np.ones(ts.size),
            "trades": np.ones(ts.size, dtype=np.int64),
        }
    )
    store.write_month(
        SYM, "1h", y, m, MonthData(df=df, source="synthetic", complete=True, sha256=None)
    )


def _setup() -> None:
    (store.binance_dir() / "catalog.json").write_text(
        json.dumps(
            {
                "fetched_at": int(time.time() * 1000),
                "symbols": [
                    {
                        "symbol": SYM,
                        "status": "TRADING",
                        "base_asset": "SYNTH",
                        "quote_asset": "USDT",
                        "step_size": 0.0001,
                        "tick_size": 0.01,
                        "min_notional": 5.0,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    _write_synthetic_month(2024, 1, 1)
    _write_synthetic_month(2024, 2, 2)


def _wait(c: TestClient, job_id: str) -> dict:
    for _ in range(600):
        s = c.get(f"/api/v1/jobs/{job_id}").json()
        if s["status"] != "running":
            return s
        time.sleep(0.2)
    raise AssertionError("el job no terminó")


def test_flujo_completo_multivariante() -> None:
    _setup()
    c = TestClient(app)
    tpl = next(t for t in c.get("/api/v1/templates").json() if t["id"] == "ema_cross_20_50")
    cfg = tpl["config"]
    cfg["symbol"] = SYM
    cfg["range"] = {"from": "2024-01-01", "to": "2024-02-29"}
    cfg["indicators"][0]["params"]["length"] = {"values": [10, 20]}
    cfg["exit"]["stop"]["pct"] = {"range": [2, 4, 2]}

    prev = c.post("/api/v1/backtests/preview", json=cfg).json()
    assert prev["n_valid"] == 4
    assert prev["data"]["available"] and prev["data"]["rows"] == (31 + 29) * 24

    job = _wait(c, c.post("/api/v1/backtests", json={"config": cfg}).json()["job_id"])
    assert job["status"] == "done", job
    bid = job["result"]["backtest_id"]

    rows = c.get(f"/api/v1/backtests/{bid}/variants?sort=total_return&desc=true").json()
    assert len(rows) == 4
    rets = [r["metrics"]["total_return"] for r in rows]
    assert rets == sorted(rets, reverse=True)

    det = c.get(f"/api/v1/backtests/{bid}/variants/{rows[0]['id']}").json()
    # El detalle recalculado coincide con lo guardado.
    assert det["metrics"]["final_equity"] == rows[0]["metrics"]["final_equity"]
    assert any("Probaste 4 variantes" in w for w in det["warnings"])
    # Conservación: capital + Σ pnl de trades = equity final.
    total_pnl = sum(t["pnl_net"] for t in det["trades"])
    assert abs(1000 + total_pnl - det["metrics"]["final_equity"]) < 1e-6
    # Desglose mensual encadenado: el último mes termina en la equity final.
    assert [m["month"] for m in det["monthly"]] == ["2024-01", "2024-02"]
    assert abs(det["monthly"][-1]["end_equity"] - det["metrics"]["final_equity"]) < 1e-9
    # Sin look-ahead en la ejecución: cada entrada es en la vela siguiente a la señal.
    for t in det["trades"]:
        assert t["entry_ts"] == t["signal_ts"] + 3_600_000

    hist = c.get("/api/v1/backtests").json()
    assert hist[0]["id"] == bid and hist[0]["status"] == "done"
