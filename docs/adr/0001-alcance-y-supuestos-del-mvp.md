# ADR 0001 — Alcance y supuestos del MVP (04/11/2026)

**Contexto.** Hubo que entregar un MVP de punta a punta en un día (`PROMPT_MVP_HOY.md`). Estas decisiones
no están en `docs/` o se apartan de ahí a propósito. Todas eligen la opción conservadora cuando hay duda.

## Datos
- **Se baja el timeframe elegido directo** (no 1m + resample, como pide `01_ESPECIFICACION §4.1`). Ruta:
  `<datos>/data/binance/spot/klines_<tf>/<SÍMBOLO>/<AAAA-MM>.parquet` + `_manifest.json` por serie.
- Mes cerrado → ZIP mensual + `.CHECKSUM`. Si el ZIP no existe todavía (mes recién terminado), el mes se
  baja de la API REST (`data-api.binance.vision`). Mes en curso → REST, marcado "incompleto" y se vuelve a
  bajar en la próxima descarga. La vela que todavía no cerró se descarta.
- El catálogo sale de `data-api.binance.vision/api/v3/exchangeInfo` (mismo contenido público que
  `api.binance.com`). Sin internet se usa la caché vieja con su fecha real.
- Las descargas corren con 4 hilos; la escritura del manifiesto va con lock (bug real encontrado en Windows).

## Motor (spot, solo long, sin bar magnifier)
- Señal al cierre de `t` → orden en el open de `t+1` con slippage en contra.
- Stop y TP con high/low de la vela. **Si se tocan los dos en la misma vela, se asume el stop** y se cuenta
  como ambiguo (sin datos de 1m no se puede saber cuál fue primero).
- Gap a través del stop → se vende al open. El TP (límite) se ejecuta a su precio y no mejora por gap.
- **Todas las órdenes pagan comisión taker, incluido el TP** (en Binance podría ser maker: favorecería al usuario).
- Stops, salidas por señal y cierre al final pagan slippage. El TP no (es límite).
- **La equity de cada vela valúa la posición a valor de liquidación** (close − slippage − comisión), así el
  drawdown no queda subestimado y el último punto coincide con el cierre real.
- Stop por ATR: usa el ATR de la vela de la señal (ya cerrada). Sin ATR (warmup) no se entra.
- Con el 100% del capital, la cantidad se achica para que la comisión entre en el efectivo.
- Cantidad redondeada hacia abajo al `stepSize`; si el notional queda bajo el mínimo, la entrada se omite y se cuenta.
- EMA y medias de Wilder (RSI, ATR) sembradas con la SMA de los primeros N valores. Bollinger con desvío poblacional.
- En spot, las condiciones "short" del esquema funcionan solo como **señal opuesta** para cerrar el long.

## Multi-variante y persistencia
- Tope de 2.000 variantes. Valores fuera de rango son error; combinaciones degeneradas (dos indicadores
  idénticos comparados entre sí, MACD rápida ≥ lenta) se descartan y se cuentan.
- Parámetros de opciones inactivas (p. ej. `stop.pct` con stop por ATR) no multiplican variantes.
- Se guardan las métricas de todas las variantes en SQLite. **Trades y equity no se guardan**: se recalculan
  bajo demanda (el motor es determinista) y antes se verifica que la huella de los datos (`data_fingerprint`)
  no haya cambiado; si cambió, se avisa en vez de mostrar un resultado distinto.
- Los datos van a cada proceso del pool por `initargs` (sin memoria compartida todavía).
- Los jobs viven en memoria: si se reinicia el backend, se pierde el progreso de un job en curso.

## Frontend
- TypeScript 5.9 (no 7) porque `openapi-typescript` todavía requiere TS 5.
- Dependencias que agregó `shadcn init` (preset Nova): `radix-ui`, `lucide-react`, `class-variance-authority`,
  `clsx`, `tailwind-merge`, `tw-animate-css`, `@fontsource-variable/geist` (MIT / ISC / OFL para la fuente).
  `@playwright/test` (Apache-2.0) para el e2e. Todas compatibles con GPL-3.0. Falta la auditoría formal (fase 7).
- Formulario con estado de React propio (sin React Hook Form + Zod todavía); la validación la hace el backend
  en el preview, que además da el contador de variantes en vivo.

## Bot
- Solo 3 herramientas de lectura (`listar_backtests`, `obtener_backtest`, `desglose_mensual`), respuesta
  completa (sin streaming), sin verificador de cifras todavía. API key en el keyring de Windows.
