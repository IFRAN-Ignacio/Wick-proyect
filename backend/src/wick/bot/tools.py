"""Herramientas de lectura del bot (MVP). Llaman a `services/`, nunca a `engine/` directo.

Toda cifra que el bot puede mostrar sale de acá.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from wick.services import backtest_service

DECLARATIONS: list[dict[str, Any]] = [
    {
        "name": "listar_backtests",
        "description": "Lista los backtests guardados en WICK con id, nombre, símbolo, "
        "timeframe, rango, cantidad de variantes y mejor retorno total (fracción: 0.12 = 12%).",
        "parameters_json_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "obtener_backtest",
        "description": "Config, avisos y métricas de la mejor variante de un backtest. "
        "Retornos y drawdown son fracciones (0.12 = 12%).",
        "parameters_json_schema": {
            "type": "object",
            "properties": {"id": {"type": "string", "description": "id del backtest"}},
            "required": ["id"],
        },
    },
    {
        "name": "desglose_mensual",
        "description": "Retorno (fracción) y trades por mes de la mejor variante de un backtest.",
        "parameters_json_schema": {
            "type": "object",
            "properties": {"id": {"type": "string", "description": "id del backtest"}},
            "required": ["id"],
        },
    },
]


def listar_backtests() -> dict[str, Any]:
    rows = backtest_service.list_backtests(limit=30)
    keep = (
        "id",
        "name",
        "symbol",
        "timeframe",
        "range_from",
        "range_to",
        "n_variants",
        "status",
        "created_at",
        "best_return",
    )
    return {"backtests": [{k: r[k] for k in keep} for r in rows]}


def _best(bt_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    bt = backtest_service.get_backtest(bt_id)
    if bt is None or not bt["best_variant_id"]:
        raise KeyError(f"No existe el backtest {bt_id} o no tiene variantes.")
    return bt, backtest_service.variant_detail(bt_id, bt["best_variant_id"])


def obtener_backtest(id: str) -> dict[str, Any]:
    bt, det = _best(id)
    return {
        "id": bt["id"],
        "nombre": bt["name"],
        "simbolo": bt["symbol"],
        "timeframe": bt["timeframe"],
        "rango": [bt["range_from"], bt["range_to"]],
        "variantes_probadas": bt["n_variants"],
        "mejor_variante_parametros": det["params"],
        "metricas_mejor_variante": det["metrics"],
        "avisos": det["warnings"],
    }


def desglose_mensual(id: str) -> dict[str, Any]:
    _bt, det = _best(id)
    return {"id": id, "meses": det["monthly"]}


REGISTRY: dict[str, Callable[..., dict[str, Any]]] = {
    "listar_backtests": listar_backtests,
    "obtener_backtest": obtener_backtest,
    "desglose_mensual": desglose_mensual,
}


def execute(name: str, args: dict[str, Any]) -> dict[str, Any]:
    fn = REGISTRY.get(name)
    if fn is None:
        return {"error": f"Herramienta desconocida: {name}"}
    try:
        return fn(**args)
    except Exception as exc:
        return {"error": str(exc)}
