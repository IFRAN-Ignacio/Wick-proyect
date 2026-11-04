from __future__ import annotations

from fastapi import APIRouter

from wick.api.models import StrategyIn, StrategyOut, TemplateOut
from wick.services import strategy_service

router = APIRouter(tags=["strategies"])


@router.get("/templates", response_model=list[TemplateOut])
def get_templates() -> list[TemplateOut]:
    return [TemplateOut.model_validate(t) for t in strategy_service.templates()]


@router.get("/strategies", response_model=list[StrategyOut])
def get_strategies() -> list[StrategyOut]:
    return [StrategyOut.model_validate(s) for s in strategy_service.list_strategies()]


@router.post("/strategies", response_model=StrategyOut)
def post_strategy(body: StrategyIn) -> StrategyOut:
    saved = strategy_service.save(body.config, body.id)
    return StrategyOut(
        id=saved["id"], name=saved["name"], updated_at=saved["updated_at"], config=body.config
    )


@router.delete("/strategies/{strategy_id}")
def delete_strategy(strategy_id: str) -> dict[str, bool]:
    strategy_service.delete(strategy_id)
    return {"ok": True}
