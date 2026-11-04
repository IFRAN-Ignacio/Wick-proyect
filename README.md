<p align="center"><img src="frontend/public/logo.png" alt="WICK" width="260"></p>

# WICK

Backtester de estrategias de cripto **gratuito, open source (GPL-3.0-or-later) y 100% local** en Windows.
Baja datos públicos de Binance, corre una estrategia o miles de variantes en paralelo y muestra los
resultados con todos sus avisos. Incluye un asistente (Gemini) que interpreta los resultados con cifras
calculadas por la app.

> Un backtest es una simulación sobre datos pasados. No predice el futuro, no es asesoramiento
> financiero y no garantiza nada.

**Estado: MVP.** Spot, solo long. El diseño completo está en [`docs/`](docs/) y lo que se simplificó
para el MVP, en [`docs/adr/0001-alcance-y-supuestos-del-mvp.md`](docs/adr/0001-alcance-y-supuestos-del-mvp.md).

## Instalación paso a paso (Windows)

Todavía no hay instalador: se baja el proyecto, se instalan dos programas y WICK instala solo el resto
la primera vez que lo abrís.

### 1. Instalá los dos programas que necesita (una sola vez)
Abrí **PowerShell** (tecla Windows, escribí `powershell`, Enter) y corré:
```powershell
winget install astral-sh.uv
winget install OpenJS.NodeJS.LTS
```
Después **cerrá PowerShell y abrilo de nuevo** para que los reconozca. Comprobalo con
`uv --version` y `node --version`. Python no hace falta instalarlo: uv baja Python 3.12 solo.

### 2. Bajá WICK
- **Sin Git:** en esta página de GitHub tocá **Code → Download ZIP**, descomprimilo y dejá la carpeta
  donde quieras (por ejemplo `C:\WICK`).
- **Con Git:** `git clone https://github.com/IFRAN-Ignacio/Wick-proyect.git C:\WICK`

### 3. Abrilo
```powershell
cd C:\WICK
.\dev.ps1
```
La **primera vez** tarda unos minutos: `dev.ps1` instala solo Python 3.12 y las librerías del backend
(`uv sync`) y las de la interfaz (`npm install`). Las veces siguientes arranca en segundos.

Se abren dos ventanas (backend y frontend; **no las cierres mientras uses WICK**) y el navegador en
http://localhost:5173. Si PowerShell bloquea el script:
`powershell -ExecutionPolicy Bypass -File .\dev.ps1`.

### 4. (Opcional) Activá el asistente
Sacá una API key gratis en [Google AI Studio](https://aistudio.google.com) → **Get API key** →
**Create API key**, y pegala en WICK en **Configuración → Guardar**. Sin key, todo funciona menos el
asistente.

### 5. Usalo
Andá a **Datos**, bajá por ejemplo BTCUSDT en 1h, después a **Estrategia**, cargá una plantilla y tocá
**Correr backtest**. Todo está explicado en el [manual de usuario](MANUAL_DE_USUARIO.md).

**Para cerrar WICK:** cerrá las dos ventanas del backend y el frontend.

## Requisitos
- Windows 10/11, PowerShell.
- [uv](https://docs.astral.sh/uv/) (`winget install astral-sh.uv`). Python 3.12 lo baja uv solo.
- [Node.js](https://nodejs.org/) 20 o más nuevo (`winget install OpenJS.NodeJS.LTS`).
- Internet para la primera instalación, para bajar datos y para el asistente.

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
