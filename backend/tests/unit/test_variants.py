from __future__ import annotations

import pytest

from wick.engine import variants
from wick.engine.schema import StrategyConfig


def _cfg(**over: object) -> StrategyConfig:
    base: dict[str, object] = {
        "name": "t",
        "symbol": "BTCUSDT",
        "timeframe": "1h",
        "range": {"from": "2024-01-01", "to": "2024-02-01"},
        "capital": 1000,
        "indicators": [
            {"id": "fast", "type": "ema", "params": {"length": {"values": [10, 20, 30]}}},
            {"id": "slow", "type": "ema", "params": {"length": {"values": [50, 100]}}},
        ],
        "entry": {"long": {"conditions": [{"left": "fast", "op": "crosses_above", "right": "slow"}]}},
        "exit": {"stop": {"type": "pct", "pct": {"values": [2, 4]}}},
    }
    base.update(over)
    return StrategyConfig.model_validate(base)


def test_producto_cartesiano_12() -> None:
    exp = variants.plan(_cfg())
    assert exp.n_total == 12
    got = [v for v in variants.iterate(exp) if not isinstance(v, str)]
    assert len(got) == 12
    assert {tuple(sorted(v.params.items())) for v in got} == {
        (("fast.length", f), ("slow.length", s), ("stop.pct", p))
        for f in (10, 20, 30)
        for s in (50, 100)
        for p in (2, 4)
    }


def test_rango_con_paso_decimal() -> None:
    assert variants.range_values(1, 2, 0.1) == [1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 2.0]
    assert variants.range_values(10, 30, 10) == [10, 20, 30]


def test_parametro_inactivo_no_multiplica() -> None:
    exp = variants.plan(_cfg(exit={"stop": {"type": "none", "pct": {"values": [2, 4]}}}))
    assert exp.n_total == 6


def test_combinacion_identica_se_descarta_y_cuenta() -> None:
    cfg = _cfg(
        indicators=[
            {"id": "fast", "type": "ema", "params": {"length": {"values": [20, 50]}}},
            {"id": "slow", "type": "ema", "params": {"length": 50}},
        ]
    )
    out = list(variants.iterate(variants.plan(cfg)))
    discarded = [x for x in out if isinstance(x, str)]
    assert len(out) == 4 and len(discarded) == 2  # 2 combos con fast=50=slow (stop 2 y 4)


def test_valor_fuera_de_rango_es_error() -> None:
    with pytest.raises(ValueError):
        variants.plan(_cfg(exit={"stop": {"type": "pct", "pct": 0}}))
    with pytest.raises(ValueError):
        variants.plan(_cfg(sizing={"value": 150}))
