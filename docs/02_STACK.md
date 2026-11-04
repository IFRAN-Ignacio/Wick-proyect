# WICK — Stack tecnológico y por qué

> Cada elección tiene su razón y las alternativas descartadas. **Regla para Claude Code:** no agregar dependencias fuera de esta lista sin pedir permiso y justificar.
> Todas las dependencias deben tener licencia compatible con GPL-3.0 (MIT, BSD, Apache-2.0, ISC, PSF, LGPL). Verificarlo al agregar cada una.

---

## Resumen

```
┌──────────────────────────────────────────────────────────────┐
│  Navegador (UI)   React 19 + TypeScript + Vite + Tailwind v4 │
│                   Lightweight Charts · ECharts · TanStack    │
└───────────────▲──────────────────────────────────────────────┘
                │ HTTP + SSE en 127.0.0.1 (mismo origen, sin CORS)
┌───────────────┴──────────────────────────────────────────────┐
│  Backend local    Python 3.12 · FastAPI · Pydantic v2        │
│  Motor            NumPy + Numba (núcleo) · pandas (E/S)      │
│  Datos            Parquet (pyarrow) · SQLite (metadatos)     │
│  Bot              google-genai (Gemini) + function calling   │
└───────────────▲──────────────────────────────────────────────┘
                │ empaquetado
┌───────────────┴──────────────────────────────────────────────┐
│  PyInstaller (onedir) + launcher con ícono de bandeja        │
│  Inno Setup 6 → WICK-Setup.exe                               │
└──────────────────────────────────────────────────────────────┘
```

---

## Backend (Python)

| Pieza | Elección | Por qué | Descartado |
|---|---|---|---|
| Lenguaje | **Python 3.12** | Ecosistema numérico, lo que Iñaki ya conoce. 3.12 tiene soporte estable de Numba y wheels para Windows de todo el stack. | 3.13+: verificar soporte de Numba antes de subir |
| Entorno y deps | **uv** | Rápido, lockfile reproducible (`uv.lock`), maneja la versión de Python en Windows sin pelearse con el PATH. | pip+venv a mano, Poetry (más lento) |
| API | **FastAPI + uvicorn** | Tipado con Pydantic, genera OpenAPI automático (del que se generan los tipos TypeScript del frontend), soporta SSE. Ya se usó en WICK. | Flask (sin tipado ni OpenAPI nativos) |
| Validación | **Pydantic v2** | Define el esquema de estrategia una sola vez; valida en el backend y exporta JSON Schema. | — |
| Cálculo vectorial | **NumPy** | Base de todo: indicadores, señales, métricas. | — |
| Motor por vela | **Numba** (`@njit`, `cache=True`) | El motor es **path-dependent** (stops, trailing, liquidación, funding, bar magnifier): necesita un loop vela a vela, y en Python puro eso es ~100× más lento. Numba compila el loop a código máquina sin salir de Python. | Python puro (lento), Cython (agrega compilador C en Windows), Rust/PyO3 (curva de aprendizaje y toolchain), backtesting.py/vectorbt (cajas negras, licencias y supuestos propios: queremos un motor auditable) |
| E/S y resample | **pandas** | Lectura de CSV de Binance, resample de 1m a cualquier timeframe y desgloses por calendario. Fuera del núcleo caliente. | Polars (más rápido pero agrega una segunda API de DataFrames; no hace falta) |
| Almacenamiento de velas | **Parquet vía pyarrow** (compresión zstd) | Columnar, comprimido (las velas de 1m comprimen muy bien), lectura parcial por columnas y por partición. Estándar abierto. | CSV (pesado, lento), SQLite para velas (pesado para series largas), HDF5 (frágil en Windows) |
| Metadatos y resultados | **SQLite** (`sqlite3` de la stdlib + migraciones SQL numeradas) | Un archivo, sin servidor, transaccional. Guarda estrategias, backtests, métricas de variantes, conversaciones y estado de jobs. Modo WAL para lecturas concurrentes. | ORM pesado (SQLAlchemy: innecesario para este tamaño), Postgres (requiere servidor) |
| Arrays de resultados | **Parquet** por backtest (trades y equity) | Una tabla de trades de 10.000 filas no va en SQLite; en Parquet pesa poco y se lee rápido. | — |
| HTTP | **httpx** (async, HTTP/2) | Descargas concurrentes con límite, reintentos y timeouts. | requests (sin async) |
| Reintentos | **tenacity** | Backoff exponencial para 429/5xx de Binance y Gemini. | Lógica casera |
| Rutas del SO | **platformdirs** | `%LOCALAPPDATA%\WICK` correcto en Windows y listo para macOS/Linux a futuro. | Rutas hardcodeadas |
| API key | **keyring** (Windows Credential Manager) | La key no queda en texto plano en un archivo. | `.env` o JSON en disco |
| IA | **google-genai** (SDK oficial) | SDK oficial actual de Gemini, con function calling. Modelo por defecto `gemini-3.5-flash-lite`. | `google-generativeai` (SDK viejo), LangChain (capa innecesaria) |
| Búsqueda en la guía | **rank-bm25** | El bot busca en la guía de usuario con BM25 local: offline, sin embeddings y sin gastar cuota de API. La guía es chica y BM25 sobra. | Embeddings + vector DB (gasta cuota y suma complejidad) |
| Estadística | **`statistics.NormalDist`** (stdlib) + NumPy | Alcanza para Deflated Sharpe, Monte Carlo y percentiles. Evita SciPy (~100 MB en el instalador). | SciPy |
| Bandeja del sistema | **pystray** + Pillow | Ícono para "Abrir WICK" y "Salir": el usuario necesita una forma visible de cerrar el servidor. | Ventana de consola visible (fea, se cierra sin querer) |
| Tests | **pytest**, **hypothesis**, **pytest-benchmark** | Hypothesis genera casos para invariantes (sin look-ahead, conservación del dinero). Benchmark detecta regresiones de velocidad. | — |
| Calidad | **ruff** (lint + formato), **mypy** (modo estricto en `engine/` y `data/`) | Uno rápido para todo; tipado estricto donde un error cuesta caro. | black+flake8+isort (3 herramientas) |

### Por qué NO un backtester existente
backtesting.py, vectorbt, Backtrader, etc. traen supuestos propios (ejecución en la misma vela, fees simplificados, sin liquidación real ni funding) y sus licencias son variadas. WICK promete **honestidad auditable**: el motor tiene que ser nuestro, chico, legible y testeado contra casos calculados a mano.

### Por qué NO TA-Lib
Requiere binario C en Windows y agrega fricción al instalador. Los indicadores se implementan en NumPy/Numba propios, con tests contra valores de referencia. Además son parte del código auditable.

---

## Frontend (React)

| Pieza | Elección | Por qué | Descartado |
|---|---|---|---|
| Base | **React 19 + TypeScript + Vite** | Decisión de Iñaki (React). TS evita errores entre backend y frontend. Vite: build y dev rápidos. | CRA (muerto), Next.js (SSR innecesario, todo es local) |
| Estilos | **Tailwind CSS v4** | Ya usado en WICK. Rápido para iterar y consistente. | CSS modules |
| Componentes | **shadcn/ui** (sobre Radix) | Accesibles y copiados al repo (no son una dependencia opaca). MIT. | MUI (pesado, estética genérica) |
| Fuentes | **@fontsource** importado **desde el entrypoint JS** | Lección de WICK: el `@import` en CSS fallaba. Fuentes locales: la app funciona offline. | Google Fonts (requiere internet) |
| Ruteo | **React Router** | Estándar. | TanStack Router (bien, pero suma aprendizaje) |
| Estado del servidor | **TanStack Query** | Cache, reintentos e invalidación de datos del backend. | Fetch suelto + useEffect |
| Estado UI | **Zustand** | Mínimo, para el estado global chico (panel del bot abierto, tema, etc.). | Redux (overkill) |
| Formularios | **React Hook Form + Zod** | El editor de estrategia es un formulario enorme y dinámico; RHF lo maneja sin re-render masivo. Zod valida en el cliente. | Formik (lento con forms grandes) |
| Tipos de API | **openapi-typescript** + **openapi-fetch** | Los tipos TS se generan del OpenAPI de FastAPI: si el backend cambia, el frontend no compila. Así no hay campos que divergen en silencio. | Tipos escritos a mano |
| Gráfico de velas | **TradingView Lightweight Charts** | Gratis, rápido con cientos de miles de velas, marcadores de trades. Apache-2.0 (compatible GPL-3.0); **requiere atribución visible a TradingView**. | Gráficos de velas genéricos (lentos) |
| Otros gráficos | **Apache ECharts** (`echarts-for-react`) | Heatmaps de parámetros, heatmap mensual, dispersión, histogramas de Monte Carlo y curvas. Rinde bien con muchos puntos. Apache-2.0. | Recharts (lento con datos grandes y sin heatmap bueno) |
| Tablas | **TanStack Table + TanStack Virtual** | Tabla de 10.000 variantes o trades sin trabarse. | AG Grid (features clave pagas) |
| Markdown del bot | **react-markdown** (sin HTML crudo) | Muestra la respuesta formateada sin riesgo de inyección. | `dangerouslySetInnerHTML` |
| Tests | **Vitest** + **Testing Library**, **Playwright** (e2e) | Unit y e2e reales contra el backend levantado. | Jest (más lento con Vite) |

---

## Empaquetado e instalación (Windows)

| Pieza | Elección | Por qué |
|---|---|---|
| Congelar Python | **PyInstaller (`--onedir`)** | Python + dependencias en una carpeta, sin requerir Python instalado. `onedir` arranca mucho más rápido que `onefile` y es menos marcado por antivirus. |
| Instalador | **Inno Setup 6** | Gratuito, estándar en Windows, permite **páginas custom** (la de la API key), accesos directos, desinstalador y licencia. |
| Arranque | `WICK.exe` (launcher) | Lock de instancia única; busca un puerto libre en `127.0.0.1`; levanta uvicorn; espera a `/api/health`; abre el navegador; ícono de bandeja. Si ya está abierto, solo abre el navegador. |
| Caché de Numba | `NUMBA_CACHE_DIR=%LOCALAPPDATA%\WICK\numba_cache` | `Program Files` no es escribible y sin esto Numba recompila en cada arranque. Al iniciar, una compilación de calentamiento en segundo plano. |
| Frontend en producción | Build de Vite servido como estáticos por FastAPI | Mismo origen: **cero problemas de CORS** (lección de WICK). |
| API key en la instalación | Página custom de Inno → archivo temporal → `wick-cli set-key --from-file` → keyring → borrar el archivo | La key nunca queda en disco ni en la línea de comandos. |

### Firma de código
Sin certificado de firma, Windows SmartScreen va a advertir "editor desconocido". Para v1 se documenta en el README y la guía cómo continuar. A futuro: SignPath ofrece firma gratuita para proyectos open source.

---

## Requisitos mínimos objetivo
- Windows 10/11 de 64 bits.
- CPU de 4 núcleos y 8 GB de RAM (el motor debe ser usable en un procesador de gama de entrada de 4 núcleos).
- Disco: ~400 MB para la app, más los datos que baje el usuario. Orientativo: 1 símbolo con 1m y varios años son decenas a cientos de MB; la app calcula el número real antes de bajar.

---

## Datos de Binance (fuentes)

| Dato | Fuente principal | Complemento (días recientes) |
|---|---|---|
| Velas 1m spot | `data.binance.vision/data/spot/monthly|daily/klines/<SYM>/1m/` (ZIP + `.CHECKSUM`) | `data-api.binance.vision/api/v3/klines` (solo datos de mercado públicos) |
| Velas 1m futuros | `data.binance.vision/data/futures/um/monthly|daily/klines/<SYM>/1m/` | `fapi.binance.com/fapi/v1/klines` |
| Mark price 1m | `.../futures/um/.../markPriceKlines/<SYM>/1m/` | `fapi/v1/markPriceKlines` |
| Funding | `.../futures/um/monthly/fundingRate/<SYM>/` | `fapi/v1/fundingRate` |
| Reglas del símbolo | `api/v3/exchangeInfo`, `fapi/v1/exchangeInfo` (públicos) | — |
| Escalones de margen | **Tabla incluida en el repo** (`engine/data/leverage_brackets.json` con fecha de captura) | `fapi/v1/leverageBracket` requiere cuenta autenticada (USER_DATA), por eso no se consulta en vivo |

**Trampas conocidas que el código DEBE manejar:**
1. **Unidades de timestamp**: los archivos spot de `data.binance.vision` usan **microsegundos desde el 1/1/2025** y milisegundos antes. Detectar por magnitud, archivo por archivo, y normalizar todo a **milisegundos UTC `int64`**. Test obligatorio cruzando el límite 2024-12 / 2025-01. (Fue un bug real en WICK.)
2. **Encabezados inconsistentes**: algunos CSV traen encabezado y otros no. Detectarlo, no asumir. (Desalineación de columnas: otro bug real de WICK.)
3. **Huecos reales**: Binance tuvo caídas de mantenimiento. Se registran como huecos, **no se rellenan**.
4. **Símbolos delistados o renombrados**: el catálogo marca su estado.
5. **Archivos mensuales**: se publican días después de terminado el mes; el mes en curso se completa con archivos diarios y la API REST.
6. **Fees y escalones cambian**: se guardan con fecha y se muestran como "valores por defecto al DD/MM/AAAA, editables".
