"""Reglas → arrays booleanos de señal.

Supuesto: la señal en `i` usa solo valores con índice <= i (indicadores calculados
sobre velas cerradas). Cualquier NaN en un operando da falso (nunca verdadero por
accidente). Las condiciones de una regla se combinan con AND.
"""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import numpy.typing as npt

from wick.engine.indicators._common import F64

BOOL = npt.NDArray[np.bool_]


def _operand(value: str | float, series: Mapping[str, F64], n: int) -> F64:
    if isinstance(value, str):
        return series[value]
    return np.full(n, float(value))


def evaluate(left: F64, op: str, right: F64) -> BOOL:
    valid = ~np.isnan(left) & ~np.isnan(right)
    if op == ">":
        return valid & (left > right)
    if op == "<":
        return valid & (left < right)
    if op in ("crosses_above", "crosses_below"):
        out = np.zeros(left.size, dtype=np.bool_)
        if left.size < 2:
            return out
        prev_valid = valid[:-1]
        if op == "crosses_above":
            hit = (left[1:] > right[1:]) & (left[:-1] <= right[:-1])
        else:
            hit = (left[1:] < right[1:]) & (left[:-1] >= right[:-1])
        out[1:] = valid[1:] & prev_valid & hit
        return out
    raise ValueError(f"Operador desconocido: {op}")


def rule_signal(
    conditions: list[tuple[str, str, str | float]],
    series: Mapping[str, F64],
    n: int,
) -> BOOL:
    """AND de condiciones (left, op, right). `right` puede ser un nombre de serie o un número."""
    sig = np.ones(n, dtype=np.bool_)
    for left, op, right in conditions:
        sig &= evaluate(_operand(left, series, n), op, _operand(right, series, n))
    return sig
