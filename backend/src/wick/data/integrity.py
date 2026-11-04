"""Detección de huecos. Los huecos se reportan; nunca se rellenan."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt


@dataclass(frozen=True)
class Gap:
    """Velas faltantes: la primera faltante abre en `from_ts`, la última en `to_ts`."""

    from_ts: int
    to_ts: int
    missing: int


def find_gaps(
    ts: npt.NDArray[np.int64],
    step_ms: int,
    expected_start: int | None,
    expected_end: int | None,
) -> list[Gap]:
    """Huecos internos entre velas consecutivas.

    Los bordes del rango (antes de la primera vela o después de la última) solo se
    cuentan si se pasa `expected_start`/`expected_end` y el símbolo ya existía,
    es decir: el borde inicial no se cuenta (el símbolo pudo listarse después).
    """
    gaps: list[Gap] = []
    if ts.size == 0:
        return gaps
    diffs = np.diff(ts)
    for idx in np.nonzero(diffs != step_ms)[0]:
        a = int(ts[idx])
        b = int(ts[idx + 1])
        missing = (b - a) // step_ms - 1
        if missing > 0:
            gaps.append(Gap(from_ts=a + step_ms, to_ts=b - step_ms, missing=missing))
    if expected_end is not None:
        last = int(ts[-1])
        missing_tail = (expected_end - last) // step_ms - 1
        if missing_tail > 0 and expected_end <= _now_floor(step_ms):
            gaps.append(
                Gap(
                    from_ts=last + step_ms,
                    to_ts=last + missing_tail * step_ms,
                    missing=missing_tail,
                )
            )
    return gaps


def _now_floor(step_ms: int) -> int:
    import time

    now = int(time.time() * 1000)
    return now - now % step_ms
