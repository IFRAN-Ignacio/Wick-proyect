"""Modelos de respuesta de la API (de acá se generan los tipos TypeScript)."""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from wick.engine.schema import StrategyConfig


class Health(BaseModel):
    status: str
    version: str
    engine_version: str


class SymbolOut(BaseModel):
    symbol: str
    status: str
    base_asset: str
    quote_asset: str
    step_size: float
    tick_size: float
    min_notional: float


class CatalogOut(BaseModel):
    fetched_at: int
    total: int
    symbols: list[SymbolOut]


class GapOut(BaseModel):
    from_ts: int
    to_ts: int
    missing: int


class DatasetOut(BaseModel):
    symbol: str
    timeframe: str
    months: list[str]
    incomplete_months: list[str]
    rows: int
    bytes: int
    first_ts: int | None
    last_ts: int | None
    gaps: list[GapOut]
    n_gaps: int
    missing_candles: int


class DownloadIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    symbol: str = Field(pattern=r"^[A-Z0-9]{2,30}$")
    timeframe: str
    from_: date = Field(alias="from")
    to: date


class JobOut(BaseModel):
    id: str
    kind: str
    status: str
    done: int
    total: int
    message: str
    error: str | None
    result: dict[str, Any]
    log: list[str]


class TemplateOut(BaseModel):
    id: str
    title: str
    description: str
    config: StrategyConfig


class StrategyOut(BaseModel):
    id: str
    name: str
    updated_at: str
    config: StrategyConfig


class StrategyIn(BaseModel):
    config: StrategyConfig
    id: str | None = None


class AxisOut(BaseModel):
    label: str
    values: list[float]


class DiscardOut(BaseModel):
    reason: str
    count: int


class PreviewData(BaseModel):
    available: bool
    rows: int
    first_ts: int | None = None
    last_ts: int | None = None
    warnings: list[str]


class PreviewOut(BaseModel):
    n_total: int
    n_valid: int
    n_discarded: int
    discard_reasons: list[DiscardOut]
    axes: list[AxisOut]
    max_variants: int
    over_cap: bool
    data: PreviewData


class BacktestIn(BaseModel):
    config: StrategyConfig
    strategy_id: str | None = None


class Metrics(BaseModel):
    total_return: float
    final_equity: float
    max_dd: float
    win_rate: float | None
    profit_factor: float | None
    profit_factor_infinite: bool
    n_trades: int
    n_wins: int
    n_losses: int
    sharpe: float | None
    fees_paid: float
    n_ambiguous: int
    n_skipped_min_notional: int
    buy_hold_return: float
    exposure: float
    net_pnl: float


class BacktestSummary(BaseModel):
    id: str
    strategy_id: str | None
    name: str
    symbol: str
    timeframe: str
    range_from: str
    range_to: str
    n_variants: int
    n_discarded: int
    status: str
    error: str | None
    created_at: str
    duration_s: float | None
    best_return: float | None
    engine_version: str


class BacktestDetail(BacktestSummary):
    config: StrategyConfig
    data_info: dict[str, Any]
    best_variant_id: str | None
    warnings: list[str]


class VariantRow(BaseModel):
    id: str
    idx: int
    params: dict[str, float]
    metrics: Metrics


class TradeOut(BaseModel):
    signal_ts: int
    entry_ts: int
    exit_ts: int
    entry_price: float
    exit_price: float
    qty: float
    fees: float
    pnl_net: float
    return_pct: float
    reason: str
    ambiguous: bool


class MonthOut(BaseModel):
    month: str
    return_: float = Field(alias="return")
    start_equity: float
    end_equity: float
    n_trades: int
    net_pnl: float
    n_wins: int

    model_config = ConfigDict(populate_by_name=True)


class EquityOut(BaseModel):
    ts: list[int]
    values: list[float]


class CandlesOut(BaseModel):
    ts: list[int]
    open: list[float]
    high: list[float]
    low: list[float]
    close: list[float]
    truncated: bool


class OverlayOut(BaseModel):
    name: str
    values: list[float | None]


class VariantDetail(BaseModel):
    id: str
    backtest_id: str
    params: dict[str, float]
    config: StrategyConfig
    metrics: Metrics
    warnings: list[str]
    trades: list[TradeOut]
    monthly: list[MonthOut]
    equity: EquityOut
    candles: CandlesOut
    overlays: list[OverlayOut]


class JobStarted(BaseModel):
    job_id: str


class BotStatus(BaseModel):
    configured: bool
    model: str
    available: bool
    message: str


class BotMessage(BaseModel):
    role: str
    text: str


class BotChatIn(BaseModel):
    messages: list[BotMessage]


class BotChatOut(BaseModel):
    text: str
    tool_calls: list[str]


class ApiKeyIn(BaseModel):
    api_key: str = Field(min_length=10, max_length=200)
