"""Golden tests del núcleo con velas SINTÉTICAS (marcadas como tales) y resultados a mano.

Convención de los casos: capital 1000, 100% del capital, sin stepSize ni mínimo.
"""

from __future__ import annotations

import numpy as np
import pytest

from wick.engine import core


def _sim(
    o: list[float],
    h: list[float],
    lo: list[float],
    c: list[float],
    entry: list[bool],
    exit_: list[bool] | None = None,
    *,
    taker: float = 0.0,
    slip: float = 0.0,
    stop_type: int = core.STOP_NONE,
    stop_pct: float = 0.0,
    tp_type: int = core.TP_NONE,
    tp_pct: float = 0.0,
    tp_rr: float = 0.0,
    use_exit: bool = False,
    size: float = 1.0,
    atr: list[float] | None = None,
    stop_mult: float = 0.0,
):
    n = len(o)
    arr = lambda x: np.array(x, dtype=np.float64)  # noqa: E731
    return core.simulate(
        arr(o),
        arr(h),
        arr(lo),
        arr(c),
        np.array(entry, dtype=np.bool_),
        np.array(exit_ if exit_ else [False] * n, dtype=np.bool_),
        arr(atr) if atr else np.full(n, np.nan),
        1000.0,
        size,
        True,
        taker,
        slip,
        stop_type,
        stop_pct,
        stop_mult,
        tp_type,
        tp_pct,
        tp_rr,
        use_exit,
        0.0,
        0.0,
    )


def test_entrada_y_salida_simple_con_costos() -> None:
    # SINTÉTICO. Señal en la vela 0 → entra en el open de la vela 1 (100).
    # Señal opuesta en la vela 2 → sale en el open de la vela 3 (120).
    o = [90, 100, 110, 120, 125]
    h = [95, 105, 115, 125, 130]
    lo = [85, 95, 105, 115, 120]
    c = [92, 102, 112, 122, 127]
    entry = [True, False, False, False, False]
    exit_ = [False, False, True, False, False]
    eq, tr, cnt = _sim(o, h, lo, c, entry, exit_, taker=0.001, slip=0.0005, use_exit=True)
    assert tr.shape[0] == 1
    entry_price = 100 * 1.0005  # 100.05
    # Con el 100% del capital el fee no entra: se achica la cantidad para poder pagarlo.
    qty = 1000 / (entry_price * 1.001)
    fee_in = qty * entry_price * 0.001
    exit_price = 120 * (1 - 0.0005)  # 119.94
    fee_out = qty * exit_price * 0.001
    assert tr[0, 0] == 1 and tr[0, 1] == 3
    assert tr[0, 2] == pytest.approx(entry_price)
    assert tr[0, 3] == pytest.approx(exit_price)
    assert tr[0, 4] == pytest.approx(qty)
    assert tr[0, 5] == pytest.approx(fee_in)
    assert tr[0, 6] == pytest.approx(fee_out)
    pnl = (exit_price - entry_price) * qty - fee_in - fee_out
    assert tr[0, 7] == pytest.approx(pnl)
    assert tr[0, 8] == core.EXIT_SIGNAL
    assert eq[-1] == pytest.approx(1000 + pnl)
    assert eq[0] == 1000  # antes de entrar
    assert cnt[0] == 0


def test_stop_loss() -> None:
    # SINTÉTICO. Entra en 100 (open vela 1). Stop 5% → 95. La vela 2 baja a 94 → sale a 95.
    o = [100, 100, 99, 90]
    h = [101, 101, 100, 91]
    lo = [99, 98, 94, 89]
    c = [100, 99, 96, 90]
    eq, tr, _ = _sim(
        o, h, lo, c, [True, False, False, False], stop_type=core.STOP_PCT, stop_pct=0.05
    )
    assert tr.shape[0] == 1
    assert tr[0, 1] == 2
    assert tr[0, 3] == pytest.approx(95.0)
    assert tr[0, 8] == core.EXIT_STOP
    assert tr[0, 7] == pytest.approx(10 * (95 - 100))  # qty = 10
    assert eq[-1] == pytest.approx(950.0)


def test_take_profit() -> None:
    # SINTÉTICO. Entra en 100. TP 10% → 110. La vela 2 llega a 112 → sale a 110 exacto.
    o = [100, 100, 105, 111]
    h = [101, 104, 112, 113]
    lo = [99, 99, 104, 109]
    c = [100, 103, 111, 112]
    eq, tr, _ = _sim(o, h, lo, c, [True, False, False, False], tp_type=core.TP_PCT, tp_pct=0.10)
    assert tr.shape[0] == 1
    assert tr[0, 1] == 2
    assert tr[0, 3] == pytest.approx(110.0)
    assert tr[0, 8] == core.EXIT_TP
    assert eq[-1] == pytest.approx(1100.0)


def test_stop_y_tp_en_la_misma_vela_asume_stop_y_cuenta_ambiguo() -> None:
    # SINTÉTICO. Entra en 100; stop 5% (95) y TP 10% (110). La vela 2 va de 90 a 115.
    o = [100, 100, 100, 100]
    h = [101, 101, 115, 101]
    lo = [99, 99, 90, 99]
    c = [100, 100, 100, 100]
    eq, tr, cnt = _sim(
        o,
        h,
        lo,
        c,
        [True, False, False, False],
        stop_type=core.STOP_PCT,
        stop_pct=0.05,
        tp_type=core.TP_PCT,
        tp_pct=0.10,
    )
    assert tr.shape[0] == 1
    assert tr[0, 8] == core.EXIT_STOP
    assert tr[0, 9] == 1
    assert tr[0, 3] == pytest.approx(95.0)
    assert cnt[0] == 1
    assert eq[-1] == pytest.approx(950.0)


def test_gap_a_traves_del_stop_ejecuta_en_el_open() -> None:
    # SINTÉTICO. Entra en 100, stop 5% (95). La vela 2 ABRE en 90: se vende a 90, no a 95.
    o = [100, 100, 90, 90]
    h = [101, 101, 92, 91]
    lo = [99, 99, 88, 89]
    c = [100, 100, 91, 90]
    eq, tr, _ = _sim(
        o, h, lo, c, [True, False, False, False], stop_type=core.STOP_PCT, stop_pct=0.05
    )
    assert tr[0, 3] == pytest.approx(90.0)
    assert eq[-1] == pytest.approx(900.0)


def test_cierre_al_final_del_periodo() -> None:
    # SINTÉTICO. Entra en 100 y nunca sale: se cierra al close de la última vela (130).
    o = [100, 100, 110, 120]
    h = [101, 111, 121, 131]
    lo = [99, 99, 109, 119]
    c = [100, 110, 120, 130]
    eq, tr, _ = _sim(o, h, lo, c, [True, False, False, False])
    assert tr.shape[0] == 1
    assert tr[0, 8] == core.EXIT_END
    assert tr[0, 3] == pytest.approx(130.0)
    assert eq[-1] == pytest.approx(1300.0)
    # Equity intermedia a valor de mercado (costos 0): 10 × close.
    assert list(eq) == pytest.approx([1000.0, 1100.0, 1200.0, 1300.0])


def test_senal_en_la_ultima_vela_no_opera() -> None:
    o = [100, 100]
    eq, tr, _ = _sim(o, [101, 101], [99, 99], [100, 100], [False, True])
    assert tr.shape[0] == 0
    assert eq[-1] == 1000.0


def test_stop_atr_usa_el_atr_de_la_vela_de_senal() -> None:
    # SINTÉTICO. ATR de la vela de señal (0) = 4, mult 2 → stop = 100 − 8 = 92.
    o = [100, 100, 95, 95]
    h = [101, 101, 96, 96]
    lo = [99, 99, 91, 94]
    c = [100, 100, 95, 95]
    _, tr, _ = _sim(
        o,
        h,
        lo,
        c,
        [True, False, False, False],
        stop_type=core.STOP_ATR,
        stop_mult=2.0,
        atr=[4.0, 50.0, 50.0, 50.0],
    )
    assert tr[0, 3] == pytest.approx(92.0)
    assert tr[0, 1] == 2


def test_tp_por_relacion_riesgo_beneficio() -> None:
    # SINTÉTICO. Entrada 100, stop 5% (95) → riesgo 5; RR 2 → TP = 110.
    o = [100, 100, 100]
    h = [101, 111, 101]
    lo = [99, 99, 99]
    c = [100, 100, 100]
    _, tr, _ = _sim(
        o,
        h,
        lo,
        c,
        [True, False, False],
        stop_type=core.STOP_PCT,
        stop_pct=0.05,
        tp_type=core.TP_RR,
        tp_rr=2.0,
    )
    assert tr[0, 8] == core.EXIT_TP
    assert tr[0, 3] == pytest.approx(110.0)


def test_step_size_y_minimo_notional() -> None:
    n = 3
    arr = lambda x: np.array(x, dtype=np.float64)  # noqa: E731
    args = (
        arr([100, 100, 100]),
        arr([101] * n),
        arr([99] * n),
        arr([100] * n),
        np.array([True, False, False]),
        np.zeros(n, dtype=np.bool_),
        np.full(n, np.nan),
        1000.0,
        0.5,
        True,
        0.0,
        0.0,
        0,
        0.0,
        0.0,
        0,
        0.0,
        0.0,
        False,
    )
    # stepSize 0.3: 500/100 = 5 → floor(5/0.3)*0.3 = 4.8
    _, tr, _ = core.simulate(*args, 0.3, 0.0)
    assert tr[0, 4] == pytest.approx(4.8)
    # mínimo 600 USDT > 500 → se omite y se cuenta
    _, tr, cnt = core.simulate(*args, 0.0, 600.0)
    assert tr.shape[0] == 0
    assert cnt[1] == 1
