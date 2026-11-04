"""Servicio de backtests: preview, corrida multi-variante en paralelo, historial y detalle."""

from __future__ import annotations

import json
import os
import time
import uuid
from collections import Counter
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from datetime import UTC, datetime
from typing import Any

import numpy as np

from wick.data import catalog, store
from wick.data.parsing import DataError
from wick.db.connection import connect
from wick.engine import backtest, core, variants
from wick.engine.backtest import IndicatorCache, Market
from wick.engine.schema import StrategyConfig
from wick.jobs.registry import Job
from wick.services import data_service, strategy_service

SMALL_SAMPLE = 30
MAX_CHART_CANDLES = 300_000
OVERFIT_TEXT = (
    "Probaste {n} variantes: que la mejor gane es esperable aunque la estrategia "
    "no tenga ventaja real."
)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


# ---------------------------------------------------------------- datos
def load_market(config: StrategyConfig) -> tuple[Market, store.LoadedSeries]:
    start, end = data_service.range_to_ms(config.range.from_, config.range.to)
    series = store.load_range(config.symbol, config.timeframe, start, end)
    info = catalog.find_symbol(data_service.source(), config.symbol)
    if info is None:
        raise DataError(f"No encuentro las reglas de {config.symbol} en el catálogo de Binance.")
    df = series.df
    market = Market(
        ts=df["ts"].to_numpy(np.int64),
        open=df["open"].to_numpy(np.float64),
        high=df["high"].to_numpy(np.float64),
        low=df["low"].to_numpy(np.float64),
        close=df["close"].to_numpy(np.float64),
        step_size=info.step_size,
        min_notional=info.min_notional,
    )
    return market, series


def data_warnings(config: StrategyConfig, series: store.LoadedSeries) -> list[str]:
    out: list[str] = []
    start, end = data_service.range_to_ms(config.range.from_, config.range.to)
    first, last = int(series.df["ts"].iloc[0]), int(series.df["ts"].iloc[-1])
    step = int(series.df["ts"].iloc[1] - series.df["ts"].iloc[0]) if len(series.df) > 1 else 0
    if first > start:
        out.append(
            f"Los datos empiezan el {_fmt(first)}, después del inicio pedido ({_fmt(start)})."
        )
    if step and last + step < end and last + step < int(time.time() * 1000) - step:
        out.append(f"Los datos terminan el {_fmt(last)}, antes del final pedido.")
    missing = sum(g.missing for g in series.gaps)
    if missing:
        out.append(
            f"Datos incompletos: faltan {missing} velas en {len(series.gaps)} huecos "
            "(no se rellenaron; el motor salta de una vela a la siguiente)."
        )
    return out


def _fmt(ts: int) -> str:
    return datetime.fromtimestamp(ts / 1000, tz=UTC).strftime("%Y-%m-%d %H:%M UTC")


# ---------------------------------------------------------------- preview
def preview(config: StrategyConfig) -> dict[str, Any]:
    exp = variants.plan(config)
    reasons: Counter[str] = Counter()
    n_valid = 0
    if exp.n_total <= 50 * variants.MAX_VARIANTS:
        for v in variants.iterate(exp):
            if isinstance(v, str):
                reasons[v] += 1
            else:
                n_valid += 1
    data: dict[str, Any] = {"available": False, "warnings": [], "rows": 0}
    try:
        market, series = load_market(config)
        data = {
            "available": True,
            "rows": int(market.ts.size),
            "first_ts": int(market.ts[0]),
            "last_ts": int(market.ts[-1]),
            "warnings": data_warnings(config, series),
        }
    except DataError as exc:
        data["warnings"] = [str(exc)]
    return {
        "n_total": exp.n_total,
        "n_valid": n_valid,
        "n_discarded": sum(reasons.values()),
        "discard_reasons": [{"reason": r, "count": c} for r, c in reasons.most_common()],
        "axes": [{"label": a.label, "values": a.values} for a in exp.axes],
        "max_variants": variants.MAX_VARIANTS,
        "over_cap": n_valid > variants.MAX_VARIANTS,
        "data": data,
    }


# ---------------------------------------------------------------- workers
_W_MARKET: Market | None = None
_W_CACHE: IndicatorCache | None = None


def _worker_init(market: Market) -> None:
    global _W_MARKET, _W_CACHE
    _W_MARKET = market
    _W_CACHE = IndicatorCache(market)


def _worker_run(idx: int, cfg: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    assert _W_MARKET is not None and _W_CACHE is not None
    return idx, backtest.run(cfg, _W_MARKET, _W_CACHE).metrics


def n_workers() -> int:
    return max(1, (os.cpu_count() or 2) - 1)


# ---------------------------------------------------------------- run
def start(config: StrategyConfig, strategy_id: str | None, job: Job) -> dict[str, Any]:
    t0 = time.perf_counter()
    exp = variants.plan(config)
    items: list[variants.Variant] = []
    reasons: Counter[str] = Counter()
    for v in variants.iterate(exp):
        if isinstance(v, str):
            reasons[v] += 1
        else:
            items.append(v)
            if len(items) > variants.MAX_VARIANTS:
                raise ValueError(
                    f"Hay más de {variants.MAX_VARIANTS} variantes. Achicá las listas o rangos."
                )
    if not items:
        raise ValueError("Todas las combinaciones quedaron descartadas: no hay nada para correr.")
    market, series = load_market(config)
    if strategy_id is None:
        strategy_id = strategy_service.save(config, None)["id"]
    bt_id = uuid.uuid4().hex[:12]
    info = {
        "rows": int(market.ts.size),
        "first_ts": int(market.ts[0]),
        "last_ts": int(market.ts[-1]),
        "step_size": market.step_size,
        "min_notional": market.min_notional,
        "warnings": data_warnings(config, series),
        "gaps": [g.__dict__ for g in series.gaps[:200]],
        "discard_reasons": dict(reasons),
        "axes": [{"label": a.label, "values": a.values} for a in exp.axes],
    }
    with connect() as conn:
        conn.execute(
            "INSERT INTO backtest(id, strategy_id, name, symbol, timeframe, config_snapshot_json,"
            " engine_version, data_fingerprint, data_info_json, n_variants, n_discarded, status,"
            " created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                bt_id,
                strategy_id,
                config.name,
                config.symbol,
                config.timeframe,
                config.model_dump_json(by_alias=True),
                core.ENGINE_VERSION,
                series.fingerprint,
                json.dumps(info),
                len(items),
                sum(reasons.values()),
                "running",
                _now_iso(),
            ),
        )
    job.total = len(items)
    job.result = {"backtest_id": bt_id}
    try:
        results = _run_all(items, market, job)
        _save_variants(bt_id, items, results)
        status, error = "done", None
    except Exception as exc:
        status, error = "error", str(exc)
        raise
    finally:
        with connect() as conn:
            conn.execute(
                "UPDATE backtest SET status=?, error=?, duration_s=? WHERE id=?",
                (status, error, time.perf_counter() - t0, bt_id),
            )
    return {"backtest_id": bt_id, "n_variants": len(items)}


def _run_all(items: list[variants.Variant], market: Market, job: Job) -> dict[int, dict[str, Any]]:
    results: dict[int, dict[str, Any]] = {}
    if len(items) == 1:
        v = items[0]
        results[v.index] = backtest.run(v.config, market).metrics
        job.done = 1
        return results
    workers = min(n_workers(), len(items))
    job.message = f"Corriendo {len(items)} variantes en {workers} procesos"
    with ProcessPoolExecutor(
        max_workers=workers, initializer=_worker_init, initargs=(market,)
    ) as pool:
        pending = {pool.submit(_worker_run, v.index, v.config) for v in items}
        while pending:
            done, pending = wait(pending, return_when=FIRST_COMPLETED)
            for fut in done:
                idx, m = fut.result()
                results[idx] = m
                job.done += 1
    return results


def _save_variants(
    bt_id: str, items: list[variants.Variant], results: dict[int, dict[str, Any]]
) -> None:
    rows = []
    for v in items:
        m = results[v.index]
        rows.append(
            (
                f"{bt_id}-{v.index}",
                bt_id,
                v.index,
                json.dumps(v.params),
                json.dumps(v.config),
                m["total_return"],
                m["max_dd"],
                m["sharpe"],
                m["profit_factor"],
                m["win_rate"],
                m["n_trades"],
                m["n_ambiguous"],
                json.dumps(m),
            )
        )
    with connect() as conn:
        conn.executemany(
            "INSERT INTO variant(id, backtest_id, idx, params_json, config_json, total_return,"
            " max_dd, sharpe, profit_factor, win_rate, n_trades, n_ambiguous, metrics_json)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            rows,
        )


# ---------------------------------------------------------------- lectura
def warnings_for(n_variants: int, m: dict[str, Any], data_warns: list[str]) -> list[str]:
    out = list(data_warns)
    if n_variants > 1:
        out.append(OVERFIT_TEXT.format(n=n_variants))
    if m["n_trades"] < SMALL_SAMPLE:
        out.append(
            f"Muestra chica: {m['n_trades']} trades (menos de {SMALL_SAMPLE}). "
            "El resultado es estadísticamente débil."
        )
    if m["n_ambiguous"]:
        out.append(
            f"{m['n_ambiguous']} salidas ambiguas: el stop y el take profit se tocaron en la "
            "misma vela y se asumió el stop (supuesto conservador)."
        )
    if m["n_skipped_min_notional"]:
        out.append(
            f"{m['n_skipped_min_notional']} entradas omitidas por no llegar al mínimo de Binance."
        )
    return out


def list_backtests(limit: int = 200) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT b.*, (SELECT MAX(total_return) FROM variant v WHERE v.backtest_id=b.id)"
            " AS best_return FROM backtest b ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [_bt_row(r) for r in rows]


def _bt_row(r: Any) -> dict[str, Any]:
    cfg = json.loads(r["config_snapshot_json"])
    return {
        "id": r["id"],
        "strategy_id": r["strategy_id"],
        "name": r["name"],
        "symbol": r["symbol"],
        "timeframe": r["timeframe"],
        "range_from": cfg["range"]["from"],
        "range_to": cfg["range"]["to"],
        "n_variants": r["n_variants"],
        "n_discarded": r["n_discarded"],
        "status": r["status"],
        "error": r["error"],
        "created_at": r["created_at"],
        "duration_s": r["duration_s"],
        "best_return": r["best_return"] if "best_return" in r.keys() else None,  # noqa: SIM118
        "engine_version": r["engine_version"],
    }


def get_backtest(bt_id: str) -> dict[str, Any] | None:
    with connect() as conn:
        r = conn.execute("SELECT * FROM backtest WHERE id=?", (bt_id,)).fetchone()
        if r is None:
            return None
        best = conn.execute(
            "SELECT id FROM variant WHERE backtest_id=? ORDER BY total_return DESC LIMIT 1",
            (bt_id,),
        ).fetchone()
    out = _bt_row(r)
    out["config"] = json.loads(r["config_snapshot_json"])
    out["data_info"] = json.loads(r["data_info_json"] or "{}")
    out["best_variant_id"] = best["id"] if best else None
    out["warnings"] = (
        [OVERFIT_TEXT.format(n=r["n_variants"])] if r["n_variants"] > 1 else []
    ) + out["data_info"].get("warnings", [])
    return out


SORTABLE = {
    "total_return",
    "max_dd",
    "sharpe",
    "profit_factor",
    "win_rate",
    "n_trades",
    "n_ambiguous",
    "idx",
}


def list_variants(
    bt_id: str, sort: str = "total_return", desc: bool = True
) -> list[dict[str, Any]]:
    if sort not in SORTABLE:
        sort = "total_return"
    order = "DESC" if desc else "ASC"
    with connect() as conn:
        rows = conn.execute(
            f"SELECT id, idx, params_json, metrics_json FROM variant WHERE backtest_id=?"
            f" ORDER BY {sort} IS NULL, {sort} {order}",
            (bt_id,),
        ).fetchall()
    return [
        {
            "id": r["id"],
            "idx": r["idx"],
            "params": json.loads(r["params_json"]),
            "metrics": json.loads(r["metrics_json"]),
        }
        for r in rows
    ]


def variant_detail(bt_id: str, variant_id: str) -> dict[str, Any]:
    """Recalcula la variante (el motor es determinista) y verifica que los datos no cambiaron."""
    with connect() as conn:
        bt = conn.execute("SELECT * FROM backtest WHERE id=?", (bt_id,)).fetchone()
        row = conn.execute(
            "SELECT * FROM variant WHERE id=? AND backtest_id=?", (variant_id, bt_id)
        ).fetchone()
    if bt is None or row is None:
        raise KeyError("No existe ese backtest o variante.")
    config = StrategyConfig.model_validate_json(bt["config_snapshot_json"])
    market, series = load_market(config)
    if series.fingerprint != bt["data_fingerprint"]:
        raise DataError(
            "Los datos guardados cambiaron desde que se corrió este backtest: "
            "no se puede reproducir exactamente. Volvé a correrlo."
        )
    cfg = json.loads(row["config_json"])
    result = backtest.run(cfg, market)
    stored = json.loads(row["metrics_json"])
    if abs(result.metrics["final_equity"] - stored["final_equity"]) > 1e-6:
        raise RuntimeError("El recálculo no coincide con el resultado guardado (bug del motor).")
    info = json.loads(bt["data_info_json"] or "{}")
    n = market.ts.size
    lo = max(0, n - MAX_CHART_CANDLES)
    cache = IndicatorCache(market)
    overlays = []
    for ind in cfg["indicators"]:
        if ind["type"] in ("sma", "ema", "bbands"):
            params = {k: float(v) for k, v in ind["params"].items()}
            for name, arr in cache.get(ind["type"], params, ind["source"]).items():
                overlays.append(
                    {
                        "name": ind["id"] if name == "" else f"{ind['id']}.{name}",
                        "values": [None if np.isnan(x) else float(x) for x in arr[lo:]],
                    }
                )
    return {
        "id": variant_id,
        "backtest_id": bt_id,
        "params": json.loads(row["params_json"]),
        "config": cfg,
        "metrics": result.metrics,
        "warnings": warnings_for(bt["n_variants"], result.metrics, info.get("warnings", [])),
        "trades": backtest.trades_table(result, market),
        "monthly": backtest.monthly_breakdown(result, market, float(cfg["capital"])),
        "equity": {"ts": market.ts.tolist(), "values": result.equity.tolist()},
        "candles": {
            "ts": market.ts[lo:].tolist(),
            "open": market.open[lo:].tolist(),
            "high": market.high[lo:].tolist(),
            "low": market.low[lo:].tolist(),
            "close": market.close[lo:].tolist(),
            "truncated": lo > 0,
        },
        "overlays": overlays,
    }
