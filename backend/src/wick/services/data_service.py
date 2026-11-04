"""Servicios de datos: catálogo, descarga incremental y listado (los usa la API y el bot)."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from datetime import UTC, date, datetime, timedelta
from typing import Any

from wick.data import catalog, store
from wick.data.parsing import DataError
from wick.data.sources.base import DataSource
from wick.data.sources.binance import BinanceSource, now_ms
from wick.data.timeframes import TIMEFRAMES
from wick.jobs.registry import Job

_source: DataSource | None = None


def source() -> DataSource:
    global _source
    if _source is None:
        _source = BinanceSource()
    return _source


def date_to_ms(d: date) -> int:
    return int(datetime(d.year, d.month, d.day, tzinfo=UTC).timestamp() * 1000)


def range_to_ms(d_from: date, d_to: date) -> tuple[int, int]:
    """Rango de fechas inclusivo [desde, hasta] → [start_ms, end_ms)."""
    if d_to < d_from:
        raise DataError("La fecha 'hasta' es anterior a 'desde'.")
    return date_to_ms(d_from), date_to_ms(d_to + timedelta(days=1))


def months_between(d_from: date, d_to: date) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    y, m = d_from.year, d_from.month
    while (y, m) <= (d_to.year, d_to.month):
        out.append((y, m))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def download(symbol: str, timeframe: str, d_from: date, d_to: date, job: Job) -> dict[str, Any]:
    if timeframe not in TIMEFRAMES:
        raise DataError(f"Timeframe no soportado: {timeframe}")
    info = catalog.find_symbol(source(), symbol)
    if info is None:
        raise DataError(f"El símbolo {symbol} no está en el catálogo spot de Binance.")
    today = datetime.now(UTC).date()
    d_to = min(d_to, today)
    months = months_between(d_from, d_to)
    now = now_ms()
    months = [
        (y, m) for (y, m) in months if store.month_bounds_ms(y, m)[0] < now
    ]
    pending = [(y, m) for (y, m) in months if not store.is_month_complete(symbol, timeframe, y, m)]
    job.total = len(pending)
    job.message = (
        f"{len(months) - len(pending)} meses ya estaban descargados; faltan {len(pending)}."
    )
    job.log.append(job.message)
    failures: list[str] = []
    empty: list[str] = []
    downloaded: list[str] = []

    def work(y: int, m: int) -> tuple[str, int, str]:
        data = source().fetch_month(symbol, timeframe, y, m)
        key = store.month_key(y, m)
        if data.df.empty:
            return key, 0, data.source
        store.write_month(symbol, timeframe, y, m, data)
        return key, len(data.df), data.source

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(work, y, m): store.month_key(y, m) for (y, m) in pending}
        for fut in as_completed(futures):
            key = futures[fut]
            try:
                k, rows, src = fut.result()
                if rows == 0:
                    empty.append(k)
                    job.log.append(f"{k}: Binance no tiene velas para este mes.")
                else:
                    downloaded.append(k)
                    job.log.append(f"{k}: {rows} velas ({'ZIP mensual' if src == 'monthly_zip' else 'API REST'}).")
            except Exception as exc:
                failures.append(f"{key}: {exc}")
                job.log.append(f"{key}: ERROR {exc}")
            job.done += 1
            job.message = f"{job.done}/{job.total} meses"
    datasets = [d for d in store.list_datasets() if d.symbol == symbol and d.timeframe == timeframe]
    result = {
        "downloaded": sorted(downloaded),
        "empty": sorted(empty),
        "failures": sorted(failures),
        "skipped_existing": len(months) - len(pending),
        "dataset": dataset_to_dict(datasets[0]) if datasets else None,
    }
    if failures:
        job.result = result
        raise DataError("Fallaron meses: " + "; ".join(sorted(failures)))
    return result


def dataset_to_dict(d: store.DatasetInfo) -> dict[str, Any]:
    out = asdict(d)
    out["gaps"] = out["gaps"][:200]
    out["n_gaps"] = len(d.gaps)
    return out


def list_datasets() -> list[dict[str, Any]]:
    return [dataset_to_dict(d) for d in store.list_datasets()]
