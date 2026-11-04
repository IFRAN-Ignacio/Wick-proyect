"""Estrategias guardadas y plantillas precargadas."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from wick.db.connection import connect
from wick.engine.schema import SCHEMA_VERSION, StrategyConfig

TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates"


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def save(config: StrategyConfig, strategy_id: str | None) -> dict[str, Any]:
    payload = config.model_dump_json(by_alias=True)
    now = _now()
    with connect() as conn:
        if (
            strategy_id
            and conn.execute("SELECT 1 FROM strategy WHERE id=?", (strategy_id,)).fetchone()
        ):
            conn.execute(
                "UPDATE strategy SET name=?, config_json=?, updated_at=? WHERE id=?",
                (config.name, payload, now, strategy_id),
            )
        else:
            strategy_id = uuid.uuid4().hex[:12]
            conn.execute(
                "INSERT INTO strategy(id, name, config_json, schema_version, source, created_at,"
                " updated_at) VALUES (?,?,?,?,?,?,?)",
                (strategy_id, config.name, payload, SCHEMA_VERSION, "user", now, now),
            )
    return {"id": strategy_id, "name": config.name, "updated_at": now}


def list_strategies() -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT id, name, config_json, updated_at FROM strategy ORDER BY updated_at DESC"
        ).fetchall()
    return [
        {
            "id": r["id"],
            "name": r["name"],
            "updated_at": r["updated_at"],
            "config": json.loads(r["config_json"]),
        }
        for r in rows
    ]


def delete(strategy_id: str) -> None:
    with connect() as conn:
        conn.execute("DELETE FROM strategy WHERE id=?", (strategy_id,))


def templates() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for f in sorted(TEMPLATES_DIR.glob("*.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        StrategyConfig.model_validate(data["config"])  # una plantilla inválida es un bug
        out.append({"id": f.stem, **data})
    return out
