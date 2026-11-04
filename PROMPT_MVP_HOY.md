# PROMPT MVP — WICK funcionando HOY

> Pegar entero en Claude Code, abierto en la carpeta del proyecto (donde están `CLAUDE.md` y `docs/`).

---

Hola. Vamos a construir **WICK**. Todo el diseño completo está en `CLAUDE.md` y `docs/`, pero **hoy tengo entrega antes de las 23:59** y necesito un **MVP que funcione de punta a punta**. No hace falta la versión completa del plan de fases.

## Cómo trabajar hoy (esto reemplaza la "Forma de trabajar" de CLAUDE.md solo para esta sesión)
- **No esperes mi aprobación entre bloques.** Trabajá de corrido, en este orden, y avisame solo si algo te bloquea de verdad.
- Siguen valiendo **todas las reglas de oro de CLAUDE.md**: nunca inventar datos, nunca decir que algo funciona sin correrlo, sin look-ahead, ante la duda lo conservador, no agregar dependencias fuera del stack.
- Prioridad absoluta: **que funcione de punta a punta**. Pulido, empaquetado, instalador, licencias y documentación de cada archivo quedan para después.
- Hacé commits chicos a medida que avanzás (`git` ya está inicializado).
- Leé rápido `CLAUDE.md`, `docs/01_ESPECIFICACION.md` y `docs/03_ARQUITECTURA.md` para respetar la estructura del repo y los nombres. El MVP tiene que ser **la base real del proyecto**, no un prototipo descartable: misma estructura de carpetas, mismo stack.

## Entorno
Windows nativo, PowerShell, sin WSL. Backend con `uv` y Python 3.12. Frontend con npm. Si falta alguna herramienta, decime el comando exacto para instalarla y esperá.

## Alcance del MVP (solo esto)

### 1. Datos (solo Binance spot)
- Catálogo de símbolos spot desde `api/v3/exchangeInfo` (público), con buscador.
- Descarga de velas del **timeframe elegido** (1m, 5m, 15m, 1h, 4h, 1d) desde `data.binance.vision` (archivos mensuales + `.CHECKSUM`), y lo del mes en curso desde `data-api.binance.vision/api/v3/klines`.
- **Trampas obligatorias** (ver `docs/02_STACK.md`): timestamps en microsegundos desde 2025-01-01 (normalizar a ms por magnitud, archivo por archivo), CSV con o sin encabezado, verificar checksum, no rellenar huecos (reportarlos).
- Guardado en Parquet según la estructura de `03_ARQUITECTURA §3`. Si ya está descargado, no se vuelve a bajar.
- Pantalla **Datos**: buscar símbolo, elegir timeframe y rango, descargar con barra de progreso y ver lo descargado.

### 2. Motor (simple pero honesto)
- Solo **spot, solo long**, una posición a la vez. Futuros, apalancamiento, funding y liquidación quedan **fuera del MVP**.
- **Indicadores**: SMA, EMA, RSI, MACD, Bollinger Bands y ATR. Nada más por ahora. Cada uno con un test contra valores calculados a mano.
- **Condiciones**: `crosses_above`, `crosses_below`, `>`, `<` entre indicador e indicador, o entre indicador y número. Varias condiciones combinadas con AND.
- **Salidas**: stop loss (% o múltiplo de ATR), take profit (% o relación riesgo/beneficio) y salida por señal opuesta opcional.
- **Tamaño**: % del capital por trade, con interés compuesto.
- **Costos**: fee taker 0,1% y slippage 0,05% por defecto, editables.
- **Reglas de ejecución** (no negociables):
  - Señal al cierre de la vela `t` → entrada en la apertura de `t+1` + slippage en contra.
  - Stops y TP se evalúan con high/low de cada vela. Si en la misma vela se tocan los dos, **se asume el stop** y se cuenta como "ambiguo".
  - Si la vela abre más allá del stop (gap), se ejecuta en el open.
  - Al final del período se cierra lo abierto al close.
- Sin bar magnifier en el MVP (va en la versión completa). El supuesto pesimista de arriba lo reemplaza de forma conservadora.
- Núcleo con NumPy + Numba según `04_PSEUDOCODIGO §5`, simplificado a spot.
- **Métricas**: retorno total, máximo drawdown, win rate, profit factor, cantidad de trades, Sharpe (diario, ×√365), fees pagados, trades ambiguos y buy & hold. Todo calculado desde la equity y los trades, nunca con el capital hardcodeado.
- **Desglose mensual** (retorno y trades por mes).
- Tests mínimos obligatorios: 4 golden tests a mano (entrada/salida simple, stop, TP, stop y TP en la misma vela), test de conservación del dinero y test de sin look-ahead.

### 3. Multi-variante (la función estrella, tiene que estar)
- Cualquier parámetro numérico de indicadores, stop, TP y % de capital puede tener una lista de valores o un rango (desde / hasta / paso).
- Producto cartesiano. Antes de correr se muestra la **cantidad de variantes**, con tope de 2.000 para el MVP.
- Correr en paralelo con `ProcessPoolExecutor` (núcleos − 1), con progreso.
- Tabla de variantes ordenable por cualquier métrica; click en una variante → su detalle.
- Aviso automático: "Probaste N variantes: que la mejor gane es esperable aunque la estrategia no tenga ventaja real."

### 4. Persistencia
- SQLite: estrategias y backtests con sus variantes y métricas (estructura simplificada de `03_ARQUITECTURA §7`).
- Historial de backtests en la UI.

### 5. Interfaz (React)
- Stack de `02_STACK.md`: React + TS + Vite + Tailwind v4 + shadcn, `@fontsource` importado desde `main.tsx`, proxy de Vite al backend (sin CORS).
- Pantallas: **Datos**, **Estrategia** (formulario: símbolo, timeframe, rango, capital, indicadores, condiciones de entrada, salidas, tamaño, costos; cada parámetro con modo "valor / lista / rango" y contador de variantes en vivo), **Resultado** (métricas, banner "Resultado sobre datos pasados. No garantiza resultados futuros.", gráfico de velas con Lightweight Charts y marcadores de entradas/salidas, curva de equity, tabla de trades, desglose mensual, tabla de variantes) e **Historial**.
- **2 plantillas** precargadas para probar en un click: "Cruce de EMAs 20/50" y "RSI 30/70".
- Todo en español, textos en `i18n/es.ts`. Modo oscuro.

### 6. Bot (solo si todo lo anterior funciona y queda tiempo)
- Panel lateral con Gemini (`gemini-3.5-flash-lite`, SDK `google-genai`). La API key se carga en una pantalla de Configuración.
- Solo 3 herramientas de lectura: `listar_backtests`, `obtener_backtest(id)` y `desglose_mensual(id)`. El bot solo interpreta las cifras que devuelven, nunca calcula, y solo habla de WICK.
- Si no hay key o no hay internet, el panel lo dice y el resto de la app funciona igual.

### Fuera del MVP (NO hacer hoy)
Futuros, apalancamiento, funding, liquidación, bar magnifier, walk-forward, Monte Carlo, DSR, comparador, exportar, instalador, launcher con bandeja, más indicadores, confirmación ponderada y documentación de cada archivo.

## Arranque
Un script `dev.ps1` en la raíz que levante backend y frontend y abra el navegador.

## Prueba final obligatoria (hacela vos antes de decir que terminaste)
1. Correr todos los tests y el lint: todo verde.
2. Con datos **reales**: bajar BTCUSDT 1h de 2023-01 a 2025-12.
3. Correr la plantilla "Cruce de EMAs 20/50" sola → mostrar las métricas reales que dio.
4. Correr una multi-variante: EMA rápida {10, 20, 30} × EMA lenta {50, 100} × stop {2%, 4%} = 12 variantes → mostrar la tabla real.
5. Verificar a mano 2 trades contra las velas guardadas (precio de entrada = open de la vela siguiente a la señal + slippage).

Al terminar, dame:
- Qué quedó funcionando y qué no (sin adornar).
- Los resultados reales de las pruebas 3 y 4.
- **Pasos exactos para que yo lo pruebe** en mi PC.
- Los comandos para subirlo a un repo nuevo de GitHub.
