"""Núcleo de simulación de WICK (MVP: spot, solo long, una posición a la vez).

Este archivo prioriza que se pueda auditar. Supuestos que implementa, todos
elegidos para NO favorecer al usuario:

1. Sin look-ahead: una señal calculada con la vela cerrada `i` se ejecuta en la
   APERTURA de la vela `i+1`, con slippage en contra.
2. Stop y take profit se evalúan con el high/low de cada vela (no hay datos
   intra-vela en el MVP). Si en la misma vela se tocan los dos, se asume que se
   tocó primero el STOP y la salida se cuenta como "ambigua".
3. Gap: si la vela abre por debajo del stop, se vende al OPEN (peor que el stop).
   El take profit es una orden límite: se ejecuta a su precio y no mejora por gap.
4. Stops y salidas a mercado pagan slippage en contra. TODAS las órdenes pagan
   la comisión taker (también el TP, aunque en Binance podría ser maker).
5. La equity de cada vela valúa la posición como si se cerrara al close pagando
   slippage y comisión (valor de liquidación), así el drawdown no se subestima.
6. Al final del período la posición abierta se cierra al close de la última
   vela, con slippage y comisión.
7. La cantidad se redondea hacia abajo al stepSize; si el notional queda por
   debajo del mínimo del símbolo, la entrada no se hace y se cuenta como omitida.
"""

from __future__ import annotations

import numpy as np
from numba import njit

# Motivos de salida
EXIT_SIGNAL = 0
EXIT_STOP = 1
EXIT_TP = 2
EXIT_END = 3
EXIT_REASONS = {EXIT_SIGNAL: "señal", EXIT_STOP: "stop", EXIT_TP: "take_profit", EXIT_END: "fin"}

STOP_NONE = 0
STOP_PCT = 1
STOP_ATR = 2
TP_NONE = 0
TP_PCT = 1
TP_RR = 2

ENGINE_VERSION = "0.1.0"


@njit(cache=True)
def _floor_step(qty: float, step: float) -> float:  # pragma: no cover - numba
    if step <= 0.0:
        return qty
    # Pequeña tolerancia para que 0.3/0.1 no se redondee a 0.2 por error de flotante.
    return float(np.floor(qty / step + 1e-9) * step)


@njit(cache=True)
def simulate(
    open_: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    entry_signal: np.ndarray,
    exit_signal: np.ndarray,
    atr: np.ndarray,
    capital: float,
    size_frac: float,
    compound: bool,
    taker: float,
    slippage: float,
    stop_type: int,
    stop_pct: float,
    stop_mult: float,
    tp_type: int,
    tp_pct: float,
    tp_rr: float,
    use_exit_signal: bool,
    step_size: float,
    min_notional: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:  # pragma: no cover - numba
    """Simula la estrategia vela a vela. Devuelve (equity, trades, contadores).

    trades: matriz (n_trades, 11) con columnas
      0 idx_entrada, 1 idx_salida, 2 precio_entrada, 3 precio_salida, 4 cantidad,
      5 fee_entrada, 6 fee_salida, 7 pnl_neto, 8 motivo, 9 ambiguo, 10 idx_señal
    contadores: [ambiguas, omitidas_por_minimo]
    """
    n = open_.size
    equity = np.empty(n)
    trades = np.zeros((n + 1, 11))
    n_trades = 0
    n_ambiguous = 0
    n_skipped = 0

    cash = capital
    in_pos = False
    qty = 0.0
    entry_price = 0.0
    entry_fee = 0.0
    entry_idx = 0
    signal_idx = 0
    stop = 0.0
    tp = 0.0
    pending_entry = False
    pending_exit = False
    pending_signal_idx = 0

    for i in range(n):
        # 1) Órdenes generadas al cierre de la vela anterior: se ejecutan en el open de i.
        if pending_exit and in_pos:
            price = open_[i] * (1.0 - slippage)
            fee = qty * price * taker
            cash += qty * price - fee
            trades[n_trades, 0] = entry_idx
            trades[n_trades, 1] = i
            trades[n_trades, 2] = entry_price
            trades[n_trades, 3] = price
            trades[n_trades, 4] = qty
            trades[n_trades, 5] = entry_fee
            trades[n_trades, 6] = fee
            trades[n_trades, 7] = (price - entry_price) * qty - entry_fee - fee
            trades[n_trades, 8] = EXIT_SIGNAL
            trades[n_trades, 9] = 0
            trades[n_trades, 10] = signal_idx
            n_trades += 1
            in_pos = False
        pending_exit = False

        if pending_entry and not in_pos:
            price = open_[i] * (1.0 + slippage)
            base = cash if compound else min(capital, cash)
            q = _floor_step(base * size_frac / price, step_size)
            if q * price * (1.0 + taker) > cash:  # no alcanza para la comisión: se achica
                q = _floor_step(cash / (price * (1.0 + taker)), step_size)
            if q <= 0.0 or q * price < min_notional:
                n_skipped += 1
            else:
                qty = q
                entry_price = price
                entry_fee = qty * price * taker
                cash -= qty * price + entry_fee
                entry_idx = i
                signal_idx = pending_signal_idx
                in_pos = True
                # El stop por ATR usa el ATR de la vela de la señal (ya cerrada).
                if stop_type == STOP_PCT:
                    stop = entry_price * (1.0 - stop_pct)
                elif stop_type == STOP_ATR:
                    stop = entry_price - stop_mult * atr[pending_signal_idx]
                else:
                    stop = 0.0
                if tp_type == TP_PCT:
                    tp = entry_price * (1.0 + tp_pct)
                elif tp_type == TP_RR:
                    tp = entry_price + tp_rr * (entry_price - stop)
                else:
                    tp = 0.0
        pending_entry = False

        # 2) Stop y take profit dentro de la vela i (orden pesimista).
        if in_pos:
            has_stop = stop_type != STOP_NONE and stop > 0.0
            has_tp = tp_type != TP_NONE
            hit_stop = has_stop and low[i] <= stop
            hit_tp = has_tp and high[i] >= tp
            if hit_stop or hit_tp:
                if hit_stop:
                    ref = open_[i] if open_[i] < stop else stop  # gap: se vende al open
                    price = ref * (1.0 - slippage)
                    reason = EXIT_STOP
                    ambiguous = 1 if hit_tp else 0
                    n_ambiguous += ambiguous
                else:
                    price = tp
                    reason = EXIT_TP
                    ambiguous = 0
                fee = qty * price * taker
                cash += qty * price - fee
                trades[n_trades, 0] = entry_idx
                trades[n_trades, 1] = i
                trades[n_trades, 2] = entry_price
                trades[n_trades, 3] = price
                trades[n_trades, 4] = qty
                trades[n_trades, 5] = entry_fee
                trades[n_trades, 6] = fee
                trades[n_trades, 7] = (price - entry_price) * qty - entry_fee - fee
                trades[n_trades, 8] = reason
                trades[n_trades, 9] = ambiguous
                trades[n_trades, 10] = signal_idx
                n_trades += 1
                in_pos = False

        # 3) Cierre de la vela i: señales para ejecutar en i+1.
        if i < n - 1:
            if in_pos and use_exit_signal and exit_signal[i]:
                pending_exit = True
            elif not in_pos and entry_signal[i]:
                pending_entry = True
                pending_signal_idx = i

        # 4) Equity a valor de liquidación al close de i.
        if in_pos:
            exit_value = qty * close[i] * (1.0 - slippage)
            equity[i] = cash + exit_value - exit_value * taker
        else:
            equity[i] = cash

    # 5) Fin del período: se cierra lo abierto al close de la última vela.
    if in_pos:
        i = n - 1
        price = close[i] * (1.0 - slippage)
        fee = qty * price * taker
        cash += qty * price - fee
        trades[n_trades, 0] = entry_idx
        trades[n_trades, 1] = i
        trades[n_trades, 2] = entry_price
        trades[n_trades, 3] = price
        trades[n_trades, 4] = qty
        trades[n_trades, 5] = entry_fee
        trades[n_trades, 6] = fee
        trades[n_trades, 7] = (price - entry_price) * qty - entry_fee - fee
        trades[n_trades, 8] = EXIT_END
        trades[n_trades, 9] = 0
        trades[n_trades, 10] = signal_idx
        n_trades += 1
        equity[i] = cash

    counters = np.array([n_ambiguous, n_skipped], dtype=np.int64)
    return equity, trades[:n_trades].copy(), counters
