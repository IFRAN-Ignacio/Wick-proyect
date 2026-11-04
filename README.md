# WICK

Backtester de estrategias de cripto **gratuito, open source (GPL-3.0-or-later) y 100% local** en Windows.
Baja datos públicos de Binance, corre una estrategia o miles de variantes en paralelo y muestra los
resultados con todos sus avisos. Incluye un asistente (Gemini) que interpreta los resultados con cifras
calculadas por la app.

> Un backtest es una simulación sobre datos pasados. No predice el futuro, no es asesoramiento
> financiero y no garantiza nada.

**Estado: MVP.** Spot, solo long. El diseño completo está en [`docs/`](docs/) y lo que se simplificó
para el MVP, en [`docs/adr/0001-alcance-y-supuestos-del-mvp.md`](docs/adr/0001-alcance-y-supuestos-del-mvp.md).

## Requisitos
- Windows 10/11, PowerShell.
- [uv](https://docs.astral.sh/uv/) (`winget install astral-sh.uv`). Python 3.12 lo baja uv solo.
- [Node.js](https://nodejs.org/) 20 o más nuevo (`winget install OpenJS.NodeJS.LTS`).

## Arrancar
```powershell
./dev.ps1
```
Levanta el backend (http://127.0.0.1:8765) y el frontend (http://localhost:5173) y abre el navegador.
Si PowerShell bloquea el script: `powershell -ExecutionPolicy Bypass -File .\dev.ps1`.

Los datos quedan en `%LOCALAPPDATA%\WICK` (velas en Parquet, `wick.db` con estrategias y backtests).

## Comandos
| | |
|---|---|
| Tests backend | `cd backend; uv run pytest` |
| Lint / tipos backend | `uv run ruff check` · `uv run mypy` |
| Tests frontend | `cd frontend; npm run test` |
| Tipos frontend | `npm run typecheck` |
| Regenerar tipos de la API | `npm run gen:api` |
| E2E (con la app levantada y BTCUSDT 1h 2023–2025 bajado) | `npx playwright test` |

## Privacidad
WICK no tiene cuentas, no recolecta datos y no envía nada a servidores propios. Los datos de mercado se
descargan de los archivos públicos de Binance. Si usás el asistente, tus mensajes y los resultados que
consulta se envían a Google (Gemini). La API key se guarda en el Administrador de credenciales de Windows.

Gráficos por [TradingView Lightweight Charts™](https://www.tradingview.com/lightweight-charts/).
