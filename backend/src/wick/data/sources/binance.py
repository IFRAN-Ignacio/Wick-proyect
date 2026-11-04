"""`BinanceSource`: única capa que habla con Binance (solo datos públicos, spot).

- Catálogo: `api/v3/exchangeInfo` (vía `data-api.binance.vision`, solo datos de mercado).
- Meses cerrados: ZIP mensual de `data.binance.vision` + `.CHECKSUM` (SHA-256).
- Mes en curso (o mes cerrado cuyo ZIP todavía no se publicó): REST `api/v3/klines`.
"""

from __future__ import annotations

import hashlib
import time
from datetime import UTC, datetime

import httpx
import pandas as pd
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from wick.data.parsing import (
    DataError,
    parse_kline_csv,
    read_single_csv_from_zip,
    rows_to_frame,
)
from wick.data.sources.base import MonthData, SymbolInfo
from wick.data.timeframes import interval_ms

VISION_BASE = "https://data.binance.vision/data/spot/monthly/klines"
REST_BASE = "https://data-api.binance.vision/api/v3"
CHECKSUM_ATTEMPTS = 3


class NotFoundError(Exception):
    pass


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, httpx.TransportError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        return code == 429 or code >= 500
    return False


def month_bounds_ms(year: int, month: int) -> tuple[int, int]:
    start = datetime(year, month, 1, tzinfo=UTC)
    end = datetime(year + 1, 1, 1, tzinfo=UTC) if month == 12 else datetime(
        year, month + 1, 1, tzinfo=UTC
    )
    return int(start.timestamp() * 1000), int(end.timestamp() * 1000)


def now_ms() -> int:
    return int(time.time() * 1000)


class BinanceSource:
    def __init__(self, client: httpx.Client | None = None) -> None:
        self._client = client or httpx.Client(timeout=httpx.Timeout(60.0, connect=15.0))

    @retry(
        retry=retry_if_exception(_is_retryable),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, max=20),
        reraise=True,
    )
    def _get(self, url: str, params: dict[str, str | int] | None = None) -> httpx.Response:
        resp = self._client.get(url, params=params)
        if resp.status_code == 404:
            raise NotFoundError(url)
        resp.raise_for_status()
        return resp

    # ---------- catálogo ----------
    def fetch_symbols(self) -> list[SymbolInfo]:
        data = self._get(f"{REST_BASE}/exchangeInfo").json()
        out: list[SymbolInfo] = []
        for s in data["symbols"]:
            filters = {f["filterType"]: f for f in s.get("filters", [])}
            lot = filters.get("LOT_SIZE", {})
            price = filters.get("PRICE_FILTER", {})
            notional = filters.get("NOTIONAL") or filters.get("MIN_NOTIONAL") or {}
            out.append(
                SymbolInfo(
                    symbol=s["symbol"],
                    status=s["status"],
                    base_asset=s["baseAsset"],
                    quote_asset=s["quoteAsset"],
                    step_size=float(lot.get("stepSize", 0.0)),
                    tick_size=float(price.get("tickSize", 0.0)),
                    min_notional=float(notional.get("minNotional", 0.0)),
                )
            )
        return out

    # ---------- velas ----------
    def fetch_month(self, symbol: str, timeframe: str, year: int, month: int) -> MonthData:
        start, end = month_bounds_ms(year, month)
        now = now_ms()
        if start >= now:
            raise DataError(f"{symbol} {year}-{month:02d}: el mes todavía no empezó.")
        if end <= now:
            try:
                df, sha = self._fetch_monthly_zip(symbol, timeframe, year, month)
                _check_inside_month(df, start, end, timeframe, f"{symbol} {year}-{month:02d}")
                return MonthData(df=df, source="monthly_zip", complete=True, sha256=sha)
            except NotFoundError:
                pass  # el ZIP no existe (mes recién cerrado o sin datos): se usa REST
        df = self.fetch_rest(symbol, timeframe, start, min(end, now))
        _check_inside_month(df, start, end, timeframe, f"{symbol} {year}-{month:02d}")
        return MonthData(df=df, source="rest", complete=end <= now, sha256=None)

    def _fetch_monthly_zip(
        self, symbol: str, timeframe: str, year: int, month: int
    ) -> tuple[pd.DataFrame, str]:
        name = f"{symbol}-{timeframe}-{year}-{month:02d}.zip"
        url = f"{VISION_BASE}/{symbol}/{timeframe}/{name}"
        expected = self._get(url + ".CHECKSUM").text.split()[0].strip().lower()
        for _attempt in range(CHECKSUM_ATTEMPTS):
            blob = self._get(url).content
            got = hashlib.sha256(blob).hexdigest()
            if got == expected:
                csv = read_single_csv_from_zip(blob, name)
                return parse_kline_csv(csv, name), got
        raise DataError(
            f"{name}: el checksum SHA-256 no coincide después de {CHECKSUM_ATTEMPTS} intentos."
        )

    def fetch_rest(self, symbol: str, timeframe: str, start: int, end: int) -> pd.DataFrame:
        """Velas en [start, end) desde la API REST. Descarta la vela que todavía no cerró."""
        step = interval_ms(timeframe)
        rows: list[list[object]] = []
        cursor = start
        now = now_ms()
        while cursor < end:
            batch = self._get(
                f"{REST_BASE}/klines",
                params={
                    "symbol": symbol,
                    "interval": timeframe,
                    "startTime": cursor,
                    "endTime": end - 1,
                    "limit": 1000,
                },
            ).json()
            if not batch:
                break
            for r in batch:
                if int(r[0]) >= end:
                    continue
                if int(r[6]) >= now:  # close_time en el futuro: vela abierta
                    continue
                rows.append(r)
            last_open = int(batch[-1][0])
            if last_open + step <= cursor:
                break
            cursor = last_open + step
        return rows_to_frame(rows, f"REST {symbol} {timeframe}")


def _check_inside_month(df: pd.DataFrame, start: int, end: int, tf: str, where: str) -> None:
    if df.empty:
        return
    ts = df["ts"].to_numpy()
    if int(ts.min()) < start or int(ts.max()) >= end:
        raise DataError(f"{where}: hay velas fuera del mes.")
    if bool(((ts - start) % interval_ms(tf) != 0).any()):
        raise DataError(f"{where}: hay velas desalineadas con el timeframe {tf}.")
