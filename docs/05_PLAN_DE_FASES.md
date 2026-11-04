# WICK — Plan de fases

> Cada fase termina con: **tests verdes + verificación manual de Iñaki + commit etiquetado**. No se arranca la fase siguiente sin su OK.
> Cada fase se divide en **bloques chicos** (½ a 1 día de trabajo cada uno). Claude Code propone los bloques de la fase al empezarla, Iñaki los aprueba y se trabaja bloque por bloque.
> Lección de WICK: la verificación manual encontró bugs que los tests no (CORS, fuentes, campos viejos, datos inventados). **No se saltea.**

---

## Fase 0 — Esqueleto y herramientas
**Objetivo:** repo vacío pero completo, que arranca y se testea.
- Monorepo según `03_ARQUITECTURA.md §2`. Licencia GPL-3.0, README mínimo, `.gitignore`, `.editorconfig`.
- Backend con uv: FastAPI con `/api/v1/health`, ruff, mypy y pytest configurados.
- Frontend con Vite + React + TS + Tailwind v4 + shadcn; `@fontsource` desde `main.tsx`; layout con sidebar y páginas vacías con rutas; archivo `i18n/es.ts`.
- Generación de tipos desde OpenAPI (`npm run gen:api`).
- Script `dev.ps1`: levanta backend y frontend (proxy de Vite → backend, sin CORS).
- SQLite con sistema de migraciones (`001_init.sql`).
- CI de GitHub Actions en **windows-latest**: lint, tipos y tests de los dos lados.

**Hecho cuando:** `dev.ps1` abre la app, el health responde y la CI pasa.

---

## Fase 1 — Datos
**Objetivo:** bajar, guardar, verificar y gestionar velas, funding y mark price.
- `DataSource` Protocol + `BinanceSource`.
- Catálogo de símbolos (spot y um) cacheado con fecha.
- Estimación de tamaño (HEAD a los archivos y suma de tamaños; factor ZIP → Parquet medido, no inventado).
- Descarga mensual/diaria con checksum, más el complemento REST para lo reciente. Actualización incremental.
- Normalización de timestamps (µs/ms) y detección de encabezados. **Tests obligatorios** con archivos reales chicos de 2024-12 y 2025-01.
- Integridad: huecos, validaciones OHLC y reporte.
- Resample a todos los timeframes, con índices a 1m.
- Jobs con progreso por SSE y cancelación.
- **UI de Datos**: buscador, estimación, descarga con progreso, lista con peso y huecos, borrar.

**Hecho cuando:** se baja BTCUSDT spot y um completo en 1m; el reporte de integridad coincide con un chequeo independiente (script aparte); el resample a 1d coincide con las velas 1d oficiales de Binance (salvo diferencias explicadas por huecos).

---

## Fase 2 — Motor (el corazón; la fase más larga)
**Objetivo:** simulación correcta, honesta y rápida de **una** variante.
- `StrategyConfig` (Pydantic) + JSON Schema.
- Indicadores (primera tanda): SMA, EMA, WMA, RSI, MACD, Bollinger, ATR, ADX/DI, Estocástico, Donchian, Keltner, VWAP (de sesión UTC), OBV, CCI, Supertrend, Ichimoku, Parabolic SAR, ROC, Williams %R, Volumen y su media. Cada uno con **tests contra valores de referencia** (calculados a mano o con una librería de referencia solo en tests).
- Señales con operadores, confirmación ponderada y warmup.
- `core.simulate` en Numba: ejecución en la vela siguiente, bar magnifier, pesimismo intra-minuto, gaps, fees, slippage, sizing, reglas del símbolo, funding, liquidación con escalones y mark price.
- Tabla `leverage_brackets.json` con fecha y fuente.
- Métricas completas y desgloses + concentración.
- **Suite de verificación del motor** (ver §Tests de motor abajo).
- Persistir un backtest simple y endpoint para correrlo.

**Hecho cuando:** pasa toda la suite de motor. Un backtest de 3 años de BTC en 1h con bar magnifier en 1m corre en **menos de 3 s** en la PC de Iñaki (después de compilar). Iñaki revisa a mano 5 trades en el gráfico de Binance y coinciden.

### Tests de motor obligatorios
1. **Golden tests a mano**: 10 o más escenarios chicos (de 5 a 30 velas sintéticas, marcadas como sintéticas) con el resultado calculado a mano en el propio test: entrada y salida simples, stop, TP, stop y TP en el mismo minuto, gap a través del stop, trailing, break-even, funding positivo y negativo, liquidación long y short, notional mínimo, spot sin margen suficiente.
2. **Sin look-ahead (property)**: alterar todas las velas posteriores a `t` no cambia ninguna decisión tomada en `≤ t`.
3. **Conservación del dinero**: `equity_final = capital + Σpnl − Σfees − Σfunding` (al centavo, con tolerancia de flotante).
4. **Costos cero**: con fees, slippage y funding en 0, buy & hold de una sola entrada coincide exactamente con el retorno del precio.
5. **Liquidación** contra la calculadora oficial de Binance (5 casos o más, anotados con fecha).
6. **Determinismo**: dos corridas devuelven el mismo resultado byte a byte.
7. **Numba vs Python**: el núcleo también corre en modo Python puro (`NUMBA_DISABLE_JIT=1`) en un test y da lo mismo.

---

## Fase 3 — Multi-variante y robustez
- `variants.expand` con valores, rangos y validación de combinaciones imposibles.
- Preview: conteo, corrida de prueba, estimación de tiempo y espacio, avisos.
- Topes (blando 10.000 con confirmación; duro configurable).
- Pool de procesos, memoria compartida, cache de indicadores y cancelación.
- Persistencia selectiva (top K) y recálculo bajo demanda.
- Out-of-sample, walk-forward, Monte Carlo y Deflated Sharpe (con el test del ejemplo del paper).
- Endpoints de heatmap, variantes y robustez.

**Hecho cuando:** 45 variantes del ejemplo de Iñaki (riesgo 1–5 × apalancamiento 3 × EMA 3) sobre 2 años de 1h corren en menos de 30 s en 4 núcleos; el recálculo de una variante no persistida da idéntico al original; cancelar funciona en menos de 2 s.

---

## Fase 4 — Interfaz completa
- **Editor de estrategia** (React Hook Form + Zod generado del JSON Schema): secciones plegables, constructor de condiciones, multivalor por parámetro (escalar / lista / rango) con **contador de variantes en vivo**, validación inline. Al cambiar el tipo de regla, se limpian los campos viejos (bug de WICK).
- Plantillas: carpeta con descripción y aviso, "usar esta plantilla".
- **Ejecutar**: pantalla de preview y confirmación.
- **Resultado**: Resumen (métricas + avisos + banner) · Gráfico (Lightweight Charts con marcadores e indicadores, con atribución a TradingView) · Trades (tabla virtualizada) · Desglose (tabla + heatmap mensual) · Variantes (tabla, heatmap 2D y dispersión) · Robustez.
- Historial (filtros, etiquetas, notas), Comparador, Configuración y Primer uso con la aceptación del aviso.
- Exportar a pedido: CSV, imagen del gráfico y reporte HTML imprimible.
- Tema claro/oscuro. Accesibilidad básica: foco visible, contraste y teclado.

**Hecho cuando:** Iñaki crea desde cero una estrategia con 3 parámetros multivalor sin leer documentación, la corre, entiende el resultado y lo compara con otra.

---

## Fase 5 — Bot
- Wrapper google-genai (`gemini-3.5-flash-lite` por defecto, configurable), manejo de 429, red y key inválida.
- Herramientas de `03_ARQUITECTURA §6.1` con validación Pydantic.
- Acciones con tarjeta de confirmación.
- Verificador de cifras.
- Guía de usuario escrita (`guide/*.md`) + índice BM25 + página Guía.
- Panel lateral con contexto de pantalla, conversaciones guardadas y estado.
- **Suite de evaluación del bot** (`tests/bot_eval/`): 30 preguntas o más con criterios (usa herramientas, no inventa cifras, rechaza temas ajenos, no recomienda invertir, pide confirmación). Se corre a mano con una key real; no corre en CI.

**Hecho cuando:** la evaluación pasa al 90% o más y con **0 cifras inventadas**. Iñaki le pregunta por su último backtest de 6 meses y el bot detecta correctamente si la ganancia se concentró en un mes.

---

## Fase 6 — Empaquetado e instalador
- Launcher: instancia única, puerto libre, token de sesión, bandeja, abrir navegador, apagado limpio.
- PyInstaller onedir; caché de Numba en LOCALAPPDATA; calentamiento en el primer arranque.
- Inno Setup: licencia, aviso, **página de API key con instrucciones paso a paso** (con opción de saltear), carpeta de datos, accesos directos, desinstalador (pregunta si borra los datos descargados).
- `build.ps1` reproducible de punta a punta.
- Prueba en **Windows limpio** (VM o Windows Sandbox) sin Python ni Node instalados.

**Hecho cuando:** en un Windows limpio, instalar → pegar key → abrir → bajar BTC → correr plantilla → preguntar al bot funciona sin tocar nada más.

---

## Fase 7 — Pulido y publicación
- Plantillas finales (de 10 a 15), revisadas una por una.
- Guía completa con capturas, FAQ y glosario.
- Revisión de todos los textos (tono, avisos, nada de "rentable").
- Auditoría de licencias de dependencias (`pip-licenses`, `license-checker`) → `THIRD_PARTY_LICENSES.txt`.
- README del repo: qué es, capturas, instalación, cómo contribuir, aviso, privacidad.
- `CONTRIBUTING.md`, plantillas de issues, `SECURITY.md`.
- Publicar en GitHub + release v1.0.0 con el instalador.
