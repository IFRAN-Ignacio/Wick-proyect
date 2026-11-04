# CLAUDE.md — Reglas permanentes del proyecto WICK

Este archivo se lee en cada sesión. Si algo acá choca con un pedido puntual, **preguntá antes de actuar**.

## Qué es
WICK: backtester de cripto (Binance), gratuito, open source (GPL-3.0), 100% local en Windows, con UI en React y asistente con Gemini. La especificación completa está en `docs/`:
- `01_ESPECIFICACION.md`: QUÉ se construye (y qué NO).
- `02_STACK.md`: tecnologías y por qué.
- `03_ARQUITECTURA.md`: módulos, flujos, datos, API.
- `04_PSEUDOCODIGO.md`: comportamiento exacto de las piezas críticas.
- `05_PLAN_DE_FASES.md`: orden de trabajo y criterios de "hecho".

Ante cualquier duda de comportamiento, **la fuente de verdad es `docs/`**. Si `docs/` está incompleto o es contradictorio, preguntale a Iñaki; no decidas en silencio.

## Entorno
- **Windows nativo**, sin WSL. Shell: PowerShell. Rutas con `pathlib`, nunca concatenando strings con `/` o `\`.
- Backend: `uv` (Python 3.12). Frontend: npm.
- Comandos: `./dev.ps1` (levantar), `uv run pytest`, `uv run ruff check`, `uv run mypy`, `npm run test`, `npm run gen:api`.

## Reglas de oro (no negociables)
1. **NUNCA inventar datos.** Si falta un dato, un archivo o una respuesta de Binance: se reporta, no se rellena, no se interpola, no se genera nada sintético. Los datos sintéticos existen **solo** en `tests/fixtures/synthetic/` y su nombre lo dice.
2. **NUNCA decir que algo funciona sin haberlo ejecutado.** "Hecho" = comando corrido + salida vista. Si no pudiste correr algo, decilo explícitamente.
3. **Sin look-ahead.** Señal con la vela cerrada `t` → ejecución en la apertura de `t+1`. Cualquier código del motor que lea índices `> t` para decidir en `t` es un bug crítico.
4. **Ante la duda, lo conservador.** Si una simplificación del motor favorece al usuario (menos costos, mejor precio de ejecución), elegí la opción que lo perjudica y documentalo.
5. **El bot nunca calcula.** Toda cifra que muestre el bot sale de una herramienta del backend.
6. **No agregar dependencias** fuera de `docs/02_STACK.md` sin pedir permiso, justificar y verificar que la licencia sea compatible con GPL-3.0.
7. **No ampliar el alcance.** Lo de "Fuera de alcance v1" (`01_ESPECIFICACION §5`) no se implementa, ni "de paso". La única preparación permitida es la interfaz `DataSource`.
8. **No tocar los tests para que pasen.** Si un test falla, se arregla el código; si creés que el test está mal, explicá por qué y esperá el OK.
9. **No borrar datos del usuario** (carpeta de datos, base SQLite) en ningún script ni test. Los tests usan directorios temporales.

## Forma de trabajar
- Se trabaja **una fase a la vez** y, dentro de la fase, **un bloque a la vez**. Al empezar una fase, proponé la lista de bloques (de ½ a 1 día cada uno) y esperá aprobación.
- Al terminar cada bloque, entregá:
  1. Qué se hizo (breve).
  2. Comandos ejecutados y resultado real (tests, lint, tipos).
  3. **Pasos de verificación manual** concretos para Iñaki ("abrí X, hacé Y, deberías ver Z").
  4. Riesgos, dudas o cosas que quedaron pendientes.
- Commits chicos y descriptivos en español (`motor: liquidación con escalones de margen`). Un tag al cerrar cada fase (`fase-2`).
- Decisiones de diseño que no están en `docs/` → un ADR corto en `docs/adr/NNNN-titulo.md`.
- Si algo del plan resulta imposible o muy distinto en la práctica (por ejemplo, un endpoint de Binance cambió), **pará y avisá** con evidencia (la respuesta real, el error real).

## Estilo de código
- Python: tipado completo; `mypy --strict` en `engine/` y `data/`; funciones chicas; docstrings en español en lo público del motor explicando **el supuesto** que implementan.
- El núcleo del motor (`engine/core.py`) prioriza **legibilidad auditable** por sobre micro-optimizaciones: alguien de la comunidad tiene que poder leerlo y verificar que no hay trampa.
- Timestamps: siempre `int64` ms UTC en el backend. Conversión a fecha legible solo en la UI. Zona horaria mostrada: UTC por defecto (configurable a local en la UI).
- Dinero y precios: `float64`, redondeo solo para mostrar. Cantidades de órdenes: redondeo hacia abajo al `stepSize`.
- TypeScript estricto. Nada de `any`. Los tipos de API se generan, no se escriben a mano.
- **Todo texto visible al usuario** va en `frontend/src/i18n/es.ts` (o en los mensajes de error del backend, en español).

## Textos y avisos
- Tono claro, cercano y sin alarmismo. Español rioplatense neutro ("vos" está bien en la UI).
- **Prohibido** describir estrategias o resultados como "rentable", "ganadora", "segura", "garantizada" o similares.
- Todo resultado lleva el banner "Resultado sobre datos pasados. No garantiza resultados futuros."
- Los avisos contextuales (sobreoptimización, muestra chica, concentración, datos incompletos) son parte del producto, no un detalle.

## Lecciones aprendidas de la versión anterior de WICK (no repetir)
- Desalineación de columnas al parsear CSV de Binance → detectar el encabezado y validar la cantidad de columnas.
- Confusión µs/ms en timestamps → normalizar por magnitud, archivo por archivo, con test.
- Pérdida silenciosa de datos en un reindex → toda transformación verifica la cantidad de filas antes y después.
- Capital hardcodeado en métricas → las métricas se calculan desde la equity y los trades.
- Faltaba el win_rate, no había rango de fechas arbitrario, asserts casi vacíos → los tests verifican valores, no solo que "no explote".
- Lógica OCO duplicada → una sola implementación de salidas.
- CORS → en dev, proxy de Vite; en producción, mismo origen.
- `@fontsource` importado en CSS no cargaba → importar desde `main.tsx`.
- Campos viejos al cambiar el tipo de regla → limpiar el estado del sub-formulario al cambiar el tipo.
- Se inventaban datos sintéticos en vez de reportar huecos → regla de oro 1.
- Faltaba el endpoint que unía el config con los datos reales → el flujo de punta a punta (UI → API → datos reales → motor → resultado) se prueba desde la fase 2.
