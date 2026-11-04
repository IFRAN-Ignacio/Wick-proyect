"""Expansión de variantes: producto cartesiano de los parámetros multivalor.

- `{"values": [...]}` → esa lista. `{"range": [a, b, paso]}` → a, a+paso, ... <= b
  (redondeado a los decimales del paso, para no arrastrar error de flotante).
- Un valor fuera de rango (por ejemplo un stop de 0%) es un ERROR del config.
- Una COMBINACIÓN imposible (por ejemplo dos EMAs idénticas comparadas entre sí)
  se descarta y se cuenta, nunca se pierde en silencio.
- Los parámetros de opciones inactivas (p. ej. `stop.pct` con stop por ATR) no
  multiplican variantes: se toma su primer valor.
"""

from __future__ import annotations

import copy
import itertools
import math
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from wick.engine.schema import StrategyConfig

MAX_VARIANTS = 2000
_INT_PARAMS = {"length", "fast", "slow", "signal", "atr_length"}

Path = tuple[str | int, ...]


@dataclass(frozen=True)
class Axis:
    path: Path
    label: str
    values: list[float]


def range_values(a: float, b: float, step: float) -> list[float]:
    decimals = _decimals(step)
    count = math.floor((b - a) / step + 1e-9) + 1
    return [round(a + k * step, decimals) for k in range(count)]


def _decimals(x: float) -> int:
    text = f"{x:.10f}".rstrip("0")
    return len(text.split(".")[1]) if "." in text else 0


def _is_multi(node: object) -> bool:
    return isinstance(node, dict) and (set(node) == {"values"} or set(node) == {"range"})


def _multi_values(node: dict[str, Any]) -> list[float]:
    if "values" in node:
        return [float(v) for v in node["values"]]
    a, b, step = node["range"]
    return range_values(float(a), float(b), float(step))


def _label(cfg: dict[str, Any], path: Path) -> str:
    if path[0] == "indicators":
        ind = cfg["indicators"][int(path[1])]
        return f"{ind['id']}.{path[3]}"
    if path[:2] == ("exit", "stop"):
        return f"stop.{path[2]}"
    if path[:2] == ("exit", "take_profit"):
        return f"tp.{path[2]}"
    if path[0] == "sizing":
        return "tamaño_pct"
    if path[0] == "entry":
        side = "entrada" if path[1] == "long" else "opuesta"
        return f"{side}[{int(path[3]) + 1}].valor"
    return ".".join(str(p) for p in path)


def _bounds(path: Path) -> tuple[float, float, bool, str]:
    """(mínimo exclusivo, máximo inclusivo, entero, nombre) para validar un valor."""
    last = str(path[-1])
    if path[0] == "indicators":
        return 0.0 if last == "mult" else 0.5, math.inf, last in _INT_PARAMS, last
    if path[:2] == ("exit", "stop"):
        if last == "pct":
            return 0.0, 99.99, False, "stop %"
        return 0.0, math.inf, last in _INT_PARAMS, f"stop {last}"
    if path[:2] == ("exit", "take_profit"):
        return 0.0, math.inf, False, f"take profit {last}"
    if path[0] == "sizing":
        return 0.0, 100.0, False, "% del capital"
    return -math.inf, math.inf, False, last


def _check_value(path: Path, v: float) -> None:
    lo, hi, integer, name = _bounds(path)
    if not math.isfinite(v) or v <= lo or v > hi:
        raise ValueError(f"Valor fuera de rango para {name}: {v}")
    if integer and v != int(v):
        raise ValueError(f"{name} tiene que ser entero: {v}")


def _set(cfg: dict[str, Any], path: Path, value: float) -> None:
    node: Any = cfg
    for p in path[:-1]:
        node = node[p]
    node[path[-1]] = value


def _get(cfg: dict[str, Any], path: Path) -> Any:
    node: Any = cfg
    for p in path:
        node = node[p]
    return node


def _inactive_paths(cfg: dict[str, Any]) -> list[Path]:
    out: list[Path] = []
    stop = cfg["exit"]["stop"]["type"]
    tp = cfg["exit"]["take_profit"]["type"]
    if stop != "pct":
        out.append(("exit", "stop", "pct"))
    if stop != "atr":
        out += [("exit", "stop", "atr_length"), ("exit", "stop", "mult")]
    if tp != "pct":
        out.append(("exit", "take_profit", "pct"))
    if tp != "rr":
        out.append(("exit", "take_profit", "ratio"))
    return out


def _walk(node: Any, path: Path, found: list[tuple[Path, Any]]) -> None:
    if _is_multi(node) or isinstance(node, int | float) and not isinstance(node, bool):
        found.append((path, node))
        return
    if isinstance(node, dict):
        for k, v in node.items():
            _walk(v, (*path, k), found)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            _walk(v, (*path, i), found)


@dataclass(frozen=True)
class Expansion:
    base: dict[str, Any]
    axes: list[Axis]
    n_total: int


def plan(config: StrategyConfig) -> Expansion:
    """Encuentra los ejes multivalor y valida todos los valores. No genera variantes."""
    cfg = config.model_dump(mode="json", by_alias=True)
    for p in _inactive_paths(cfg):
        node = _get(cfg, p)
        if _is_multi(node):
            _set(cfg, p, _multi_values(node)[0])
    leaves: list[tuple[Path, Any]] = []
    for key in ("indicators", "entry", "exit", "sizing"):
        _walk(cfg[key], (key,), leaves)
    axes: list[Axis] = []
    for path, node in leaves:
        if path[0] == "entry" and path[-1] != "value":
            continue
        values = _multi_values(node) if _is_multi(node) else [float(node)]
        for v in values:
            _check_value(path, v)
        if _is_multi(node):
            if len(set(values)) != len(values):
                raise ValueError(f"Valores repetidos en {_label(cfg, path)}.")
            axes.append(Axis(path=path, label=_label(cfg, path), values=values))
    n_total = math.prod(len(a.values) for a in axes) if axes else 1
    return Expansion(base=cfg, axes=axes, n_total=n_total)


def discard_reason(cfg: dict[str, Any]) -> str | None:
    """Combinaciones imposibles o degeneradas (se descartan y se cuentan)."""
    inds = {i["id"]: i for i in cfg["indicators"]}
    for ind in cfg["indicators"]:
        if ind["type"] == "macd" and ind["params"]["fast"] >= ind["params"]["slow"]:
            return f"{ind['id']}: la EMA rápida del MACD tiene que ser menor que la lenta"
    rules = [cfg["entry"]["long"]] + ([cfg["entry"]["short"]] if cfg["entry"]["short"] else [])
    for rule in rules:
        for c in rule["conditions"]:
            a, b = c["left"], c["right"]
            if isinstance(a, str) and isinstance(b, str) and a in inds and b in inds:
                ia, ib = inds[a], inds[b]
                if ia["type"] == ib["type"] and ia["source"] == ib["source"] and (
                    ia["params"] == ib["params"]
                ):
                    return f"{a} y {b} son idénticos (misma serie, nunca se cruzan)"
    return None


@dataclass(frozen=True)
class Variant:
    index: int
    params: dict[str, float]
    config: dict[str, Any]


def iterate(exp: Expansion) -> Iterator[Variant | str]:
    """Genera variantes concretas; para las descartadas produce el motivo (str)."""
    value_lists = [a.values for a in exp.axes]
    for idx, combo in enumerate(itertools.product(*value_lists)):
        cfg = copy.deepcopy(exp.base)
        params: dict[str, float] = {}
        for axis, v in zip(exp.axes, combo, strict=True):
            _set(cfg, axis.path, v)
            params[axis.label] = v
        reason = discard_reason(cfg)
        if reason:
            yield reason
        else:
            yield Variant(index=idx, params=params, config=cfg)
