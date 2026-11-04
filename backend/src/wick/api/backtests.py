from __future__ import annotations

from fastapi import APIRouter

from wick.api.models import (
    BacktestDetail,
    BacktestIn,
    BacktestSummary,
    JobStarted,
    PreviewOut,
    VariantDetail,
    VariantRow,
)
from wick.engine.schema import StrategyConfig
from wick.jobs.registry import registry
from wick.services import backtest_service

router = APIRouter(prefix="/backtests", tags=["backtests"])


@router.post("/preview", response_model=PreviewOut)
def post_preview(config: StrategyConfig) -> PreviewOut:
    return PreviewOut.model_validate(backtest_service.preview(config))


@router.post("", response_model=JobStarted)
def post_backtest(body: BacktestIn) -> JobStarted:
    job = registry.start(
        "backtest", lambda job: backtest_service.start(body.config, body.strategy_id, job)
    )
    return JobStarted(job_id=job.id)


@router.get("", response_model=list[BacktestSummary])
def get_backtests() -> list[BacktestSummary]:
    return [BacktestSummary.model_validate(b) for b in backtest_service.list_backtests()]


@router.get("/{bt_id}", response_model=BacktestDetail)
def get_backtest(bt_id: str) -> BacktestDetail:
    bt = backtest_service.get_backtest(bt_id)
    if bt is None:
        raise KeyError("No existe ese backtest.")
    return BacktestDetail.model_validate(bt)


@router.get("/{bt_id}/variants", response_model=list[VariantRow])
def get_variants(bt_id: str, sort: str = "total_return", desc: bool = True) -> list[VariantRow]:
    return [VariantRow.model_validate(v) for v in backtest_service.list_variants(bt_id, sort, desc)]


@router.get("/{bt_id}/variants/{variant_id}", response_model=VariantDetail)
def get_variant(bt_id: str, variant_id: str) -> VariantDetail:
    return VariantDetail.model_validate(backtest_service.variant_detail(bt_id, variant_id))
