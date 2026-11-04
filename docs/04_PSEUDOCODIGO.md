# WICK — Pseudocódigo de las piezas críticas

> Es pseudocódigo: define **comportamiento**, no implementación literal. Donde el comportamiento acá y el de `03_ARQUITECTURA.md` difieran, gana el más conservador, y hay que avisar a Iñaki.

---

## 1. Descarga e ingesta (data/sources/binance.py)

```
función descargar(mercado, simbolo, tipo, desde, hasta, progreso):
    meses = meses_entre(desde, hasta)
    faltantes = [m for m in meses if not store.existe_particion_completa(mercado, simbolo, tipo, m)]

    con concurrencia(4):                       # respetar límites, no saturar
        para cada mes en faltantes:
            si mes < mes_actual y existe_archivo_mensual(mes):
                zip, checksum = GET(url_mensual), GET(url_mensual + ".CHECKSUM")
            sino:
                zip, checksum = días diarios del mes (cada uno con su checksum)
            si sha256(zip) != checksum: reintentar 3 veces; si sigue mal → ERROR (no guardar)
            df = parsear_csv(zip)
            escribir_atomico(store.ruta(mercado, simbolo, tipo, mes), df)
            progreso(+1)

    completar_ultimas_horas_con_REST(mercado, simbolo, tipo)   # paginado, limit 1000
    integridad.recalcular(mercado, simbolo, tipo)              # huecos → tabla dataset_gap


función parsear_csv(zip):
    filas = leer_csv_sin_asumir_encabezado(zip)
    si primera_fila tiene texto no numérico: descartarla (es encabezado)
    validar cantidad de columnas == esperada para el tipo; si no → ERROR con nombre de archivo
    ts = columna_open_time como int64
    ts = normalizar_a_ms(ts)
    validar: ts estrictamente creciente; high >= max(open, close); low <= min(open, close); volume >= 0
    si alguna validación falla → ERROR (no "arreglar" en silencio)
    return df[ts, open, high, low, close, volume, trades]


función normalizar_a_ms(ts):
    # Binance spot usa microsegundos desde 2025-01-01. Decidir por magnitud, por archivo.
    si max(ts) > 1e15: return ts // 1000      # microsegundos → ms
    si max(ts) > 1e12: return ts              # ya está en ms
    ERROR("unidad de timestamp desconocida")
```

## 2. Resample (data/resample.py)

```
función resamplear(df_1m, tf):
    # Las velas de TF se anclan a la época UTC (00:00), igual que Binance.
    # 1w: anclar al lunes 00:00 UTC. 1M: primer día del mes.
    grupos = agrupar df_1m por floor(ts, tf)
    open = primer open; high = max high; low = min low; close = último close; volume = suma
    n_min = cantidad de velas de 1m en el grupo
    marcar vela como INCOMPLETA si n_min < minutos_esperados(tf)
    # Las velas incompletas por huecos se mantienen y se cuentan;
    # el resultado avisa "X velas con datos parciales".
    # La ÚLTIMA vela si todavía no cerró (tiempo real) se DESCARTA.
    también devolver: indice_inicio_1m[i], indice_fin_1m[i] para cada vela TF i
```

## 3. Expansión de variantes (engine/variants.py)

```
función expandir(config):
    ejes = []                              # (ruta_del_parámetro, lista_de_valores)
    recorrer config recursivamente:
        si nodo es {"values": L}: ejes.append((ruta, L))
        si nodo es {"range": [a, b, paso]}:
            validar paso > 0 y a <= b
            valores = a, a+paso, ... <= b (con tolerancia de flotante, redondeado a decimales del paso)
            ejes.append((ruta, valores))
    N = producto(len(v) for _, v in ejes)
    return N, generador_perezoso(producto_cartesiano(ejes))   # no materializar si N es grande

función validar_variante(v):
    # combinaciones imposibles se descartan y se CUENTAN, no fallan en silencio
    p.ej. ema_fast.length >= ema_slow.length → descartada ("rápida >= lenta")
    apalancamiento > máximo del escalón para el notional inicial → descartada
```

## 4. Señales (engine/signals.py)

```
función calcular_señales(velas_tf, indicadores_cacheados, reglas):
    para lado en [long, short]:
        si reglas[lado] es null: señal[lado] = falso en todo
        puntaje = ceros(n); obligatorias_ok = verdadero en todo
        para condición en reglas[lado].condiciones:
            r = evaluar(condición)             # array booleano, usando SOLO datos <= i
            si condición.obligatoria: obligatorias_ok &= r
            sino: puntaje += r * condición.peso
        señal[lado] = obligatorias_ok & (puntaje >= reglas[lado].min_score)
        señal[lado][:warmup] = falso           # warmup = máximo período de indicadores
    return señal_long, señal_short

operadores:
    crosses_above: a[i] > b[i] y a[i-1] <= b[i-1]
    crosses_below: simétrico
    >, <, >=, <=: comparación directa
    between: lo <= a[i] <= hi
    rising(n): a[i] > a[i-n];  falling(n): simétrico
# NaN en cualquier operando → falso (nunca verdadero por accidente)
```

## 5. Núcleo de simulación (engine/core.py, Numba)

```
función simular(velas_tf, m1, mark1m, funding, idx_1m, señales, params) -> resultado:
    efectivo = capital_inicial
    pos = ninguna        # {lado, qty, precio_entrada, margen, stop, tp, trail, liq_price, ts_entrada, ...}
    orden_pendiente = ninguna
    trades = []; equity = []

    para i en 0..n_tf-1:
        # 1) Ejecutar la orden generada al cierre de la vela anterior
        para j en idx_1m[i].inicio .. idx_1m[i].fin:
            ts = m1.ts[j]

            si j es el primer minuto de la vela i y orden_pendiente:
                ejecutar_orden(orden_pendiente, precio = m1.open[j])   # + slippage en contra + fee taker
                orden_pendiente = ninguna

            si pos:
                # 2) Funding: si ts es un timestamp de funding
                si ts in funding: aplicar_funding(pos, mark_o_close(j), tasa)
                    # pago = qty * mark * tasa; long paga si tasa > 0. Se resta/suma a pos.margen
                    # (margen aislado) y se acumula en pos.funding_total. Recalcular pos.liq_price.
                    # si esto lleva el margen a <= MM → liquidación inmediata

                # 3) Eventos intra-minuto, en orden PESIMISTA
                peor_precio = m1.low[j] si pos.long sino m1.high[j]
                mejor_precio = m1.high[j] si pos.long sino m1.low[j]
                peor_mark   = mark1m.low[j] si long sino mark1m.high[j]   (o last si no hay mark → flag)

                # gap: si el minuto ABRE más allá del stop/liq, se ejecuta en el open
                si es_futuro y toca(peor_mark, pos.liq_price):
                    liquidar(pos); continuar
                golpea_stop = pos.stop y toca(peor_precio, pos.stop)
                golpea_tp   = pos.tp   y toca(mejor_precio, pos.tp)
                si golpea_stop y golpea_tp:
                    n_ambiguos += 1
                    cerrar(pos, precio = precio_stop_con_gap(m1.open[j], pos.stop), motivo="stop (ambiguo)")
                sino si golpea_stop: cerrar(pos, precio_stop_con_gap(...), taker, motivo="stop")
                sino si golpea_tp:   cerrar(pos, pos.tp, maker, motivo="tp")
                    # el TP límite no mejora por gap: se ejecuta a pos.tp

                # 4) Actualizar trailing con el minuto YA cerrado (aplica desde el siguiente minuto)
                si pos y pos.trail: mover_stop_solo_a_favor(pos, mejor_precio)
                si pos y break_even activado y alcanzó el umbral: pos.stop = max(pos.stop, entrada ± fees)

        # 5) Al cierre de la vela TF i: salidas por tiempo y señales
        si pos y time_exit y velas_desde_entrada >= N: orden_pendiente = CERRAR
        si señal_opuesta[i] y pos y on_opposite_signal: orden_pendiente = CERRAR (+ ABRIR opuesta si corresponde)
        si no pos y no orden_pendiente:
            si señal_long[i]:  orden_pendiente = ABRIR long  (tamaño calculado al ejecutar)
            si señal_short[i] y mercado == um: orden_pendiente = ABRIR short
            # si las dos son verdaderas el mismo i: no operar y contar "señal conflictiva"

        equity.append(efectivo + pnl_no_realizado(pos, velas_tf.close[i]))
        si equity[-1] <= 0: marcar "cuenta quemada", cortar simulación

    si pos al final: cerrar al close de la última vela, motivo = "fin del período"
    return trades, equity, contadores


función ejecutar_orden ABRIR(lado, precio_ref):
    precio = precio_ref * (1 + slip) si long sino precio_ref * (1 - slip)
    stop = calcular_stop(...)  # % / ATR (ATR de la vela TF cerrada i) / nivel
    según sizing.mode:
        pct_capital: notional = equity_actual * pct * (apalancamiento si um sino 1)
        risk_pct:    qty = (equity_actual * pct) / |precio - stop|   # requiere stop
                     notional = qty * precio
                     limitar notional a equity_actual * apalancamiento (o a efectivo en spot)
        fijo:        notional = monto
    si no compound: usar capital_inicial en lugar de equity_actual
    qty = redondear_abajo(notional / precio, stepSize)
    si qty * precio < minNotional: contar "omitida por mínimo"; return
    fee = qty * precio * taker
    si um:
        margen = qty * precio / apalancamiento
        si margen + fee > efectivo: contar "omitida por margen insuficiente"; return
        efectivo -= margen + fee
        liq_price = precio_liquidación(lado, precio, qty, margen, escalon(qty*precio))
    sino:
        si qty * precio + fee > efectivo: reducir qty; recalcular
        efectivo -= qty * precio + fee
    tp = calcular_tp(...)
    pos = {...}


función precio_liquidación(lado, entrada, qty, margen, esc):   # margen aislado, un solo activo
    # Fórmula de Binance para aislado, despejada para una sola posición:
    #   long:  liq = (margen + cum - qty*entrada) / (qty*mmr - qty)
    #   short: liq = (margen + cum + qty*entrada) / (qty*mmr + qty)
    # VERIFICAR contra la calculadora oficial de Binance con al menos 5 casos y dejar los casos como test golden.


función cerrar(pos, precio, tipo_fee, motivo):
    fee = pos.qty * precio * tasa(tipo_fee)
    pnl = (precio - pos.entrada) * pos.qty * (1 si long sino -1)
    si um: efectivo += pos.margen + pnl - fee
    sino:  efectivo += pos.qty * precio - fee
    trades.append({entrada, salida, ts, qty, pnl_bruto, fees_totales, funding_total, motivo, ambiguo})


función liquidar(pos):
    # Se pierde todo el margen aislado de la posición (conservador; incluye el fee de liquidación real).
    # El margen ya se descontó del efectivo al abrir, así que no se devuelve nada.
    # El funding se suma/resta a pos.margen mientras la posición vive, así que la pérdida neta
    # respecto del efectivo antes de abrir es siempre margen_inicial + fee_entrada.
    trades.append({... precio_salida = pos.liq_price, pnl_neto = -(pos.margen_inicial + fee_entrada), funding_total (informativo), motivo="liquidación"})
    pos = ninguna
```

## 6. Métricas (engine/metrics.py)

```
retorno_total = equity_final / capital - 1
CAGR = (equity_final / capital) ^ (365.25 / días) - 1      # si días < 30 → no mostrar CAGR
retornos_diarios = equity resampleada a 1d (último valor del día) → pct_change
Sharpe = media(r_d) / std(r_d) * sqrt(365)                # cripto opera los 365 días; rf = 0
Sortino = media(r_d) / std(r_d[r_d < 0]) * sqrt(365)
max_dd = max(1 - equity / maximo_acumulado(equity));  duración = la racha más larga bajo el máximo
Calmar = CAGR / max_dd
profit_factor = suma(pnl > 0) / |suma(pnl < 0)|          # sin pérdidas → "∞", nunca error
win_rate, expectancia = media(pnl_neto), payoff = media(ganadores) / |media(perdedores)|
exposición = tiempo_en_posición / tiempo_total
buy_and_hold = close_final / close_inicial - 1 (mismos costos de 1 entrada y 1 salida)
# Todas las métricas se calculan desde la equity y los trades: nunca con el capital hardcodeado (bug de WICK).
# n_trades == 0 → métricas que no aplican = null (la UI muestra "—"), no 0.
```

## 7. Desglose y concentración (engine/breakdown.py)

```
función desglose(equity, trades, periodo ∈ {día, semana, mes, trimestre, año}):
    para cada período calendario (UTC; semana = lunes a domingo):
        retorno = equity_fin / equity_inicio - 1
        trades_cerrados, ganancia_neta, max_dd_interno, fees, funding
    return tabla

función concentracion(desglose_mensual, trades):
    ganancia_total = suma(ganancias_netas_positivas_de_meses)
    share_max_mes = max(ganancia_mes) / ganancia_total
    share_top10pct_trades = suma(top 10% trades por pnl) / suma(pnl total)
    meses_positivos / meses_totales
    aviso si share_max_mes > 0.5 o share_top10pct_trades > 1.0   # los mejores trades explican más del 100%: el resto pierde
    # Esto es lo que alimenta al bot para decir "ganó fuerte en 1 mes y el resto neutro o en pérdida".
```

## 8. Robustez (engine/robustness.py)

```
OUT-OF-SAMPLE:
    corte = desde + (hasta - desde) * (1 - fraccion)
    TODAS las variantes corren sobre [desde, corte) = in-sample
    se elige la mejor (o top K) por la métrica elegida EN in-sample
    SOLO esas se corren en [corte, hasta) = out-of-sample (estado inicial limpio, sin posición)
    mostrar IS vs OOS lado a lado + degradación %

WALK-FORWARD (ventanas ancladas o móviles):
    para cada ventana k: optimizar en train_k, evaluar la mejor en test_k (no solapadas)
    curva OOS concatenada = el resultado "honesto"
    eficiencia WF = rendimiento_OOS_anualizado / rendimiento_IS_anualizado

MONTE CARLO (bootstrap de trades):
    para s en 1..S (por defecto 1000, semilla fija → reproducible):
        muestra = trades con reemplazo (mismo n)
        equity_s = capital * prod(1 + retorno_por_trade)   # retorno relativo al equity en la entrada
        guardar retorno_final_s, max_dd_s
    mostrar percentiles 5/25/50/75/95 y P(retorno < 0)
    aviso en la UI: "asume que los trades son independientes; no captura cambios de régimen"

DEFLATED SHARPE RATIO (Bailey & López de Prado, 2014):
    entradas: SR_mejor (no anualizado, por período), T (n de retornos), asimetría γ3, curtosis γ4,
              N = variantes probadas, V = var(SR de todas las variantes)
    SR0 = sqrt(V) * ((1 - γ) * Z⁻¹(1 - 1/N) + γ * Z⁻¹(1 - 1/(N·e)))      # γ = 0.5772 (Euler–Mascheroni)
    DSR = Φ( (SR_mejor - SR0) * sqrt(T - 1) / sqrt(1 - γ3*SR_mejor + (γ4 - 1)/4 * SR_mejor²) )
    Z⁻¹ y Φ con statistics.NormalDist
    interpretación para la UI: DSR = prob. de que el Sharpe real sea > 0 descontando haber probado N variantes
        DSR < 0.5 → "muy probablemente suerte"; 0.5–0.95 → "dudoso"; > 0.95 → "resiste la corrección (no garantiza nada)"
    N = 1 → DSR = PSR (Probabilistic Sharpe) con referencia 0
    test: reproducir el ejemplo numérico del paper
```

## 9. Bot — turno (bot/)

```
SYSTEM PROMPT (resumen; texto completo en prompts.py):
  - Sos el asistente de WICK. Hablás en español rioplatense neutro, claro y sin jerga innecesaria.
  - Solo ayudás con WICK: usar la app, entender resultados, preparar estrategias, correr backtests, consultar datos descargados.
  - NUNCA calculás ni estimás números. Toda cifra sale de una herramienta. Si no tenés la herramienta para un dato, decilo.
  - NUNCA das recomendaciones de inversión, ni predicciones, ni decís que una estrategia "funciona" o "es rentable".
  - Siempre que hables de un resultado, recordá brevemente que es pasado; si hubo muchas variantes, mencioná el DSR o el OOS.
  - Temas ajenos a WICK: respondé en una línea que solo podés ayudar con WICK y ofrecé algo concreto.
  - Para correr backtests o bajar datos grandes, usá la herramienta; la app le pide confirmación al usuario.
  - Si una herramienta devuelve error o datos faltantes, explicalo; no completes con suposiciones.

función turno(conversacion, mensaje, contexto):
    si no hay key o no hay internet: devolver estado "bot no disponible" (la UI ya lo muestra)
    historial = recortar(conversacion, K) + resumen_si_hace_falta
    loop hasta 8 iteraciones:
        resp = gemini.generate(modelo, system, historial, herramientas)
        si resp tiene llamadas a herramientas:
            para cada llamada:
                validar argumentos con Pydantic (si son inválidos → devolver error a Gemini, no ejecutar)
                si es de acción: crear acción pendiente → emitir tarjeta a la UI → esperar confirmación (timeout → cancelada)
                resultado = services.ejecutar(llamada)
                historial.append(resultado)
        sino:
            texto = resp.texto
            marcas = verificador.verificar(texto, todos_los_resultados_de_herramientas)
            emitir(texto, marcas); guardar; return
    emitir("No pude completar la respuesta"); return
    errores 429/cuota → mensaje "Se agotó la cuota gratuita de tu API key por ahora. El resto de WICK sigue funcionando."
```
