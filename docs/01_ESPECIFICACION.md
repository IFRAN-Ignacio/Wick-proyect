# WICK — Especificación funcional (idea cerrada)

> Versión 1.0 · 21/10/2026 · Autor: Iñaki
> Este documento define **qué** es WICK. El **cómo** está en `02_STACK.md`, `03_ARQUITECTURA.md` y `04_PSEUDOCODIGO.md`.

---

## 1. Qué es WICK

WICK es un **backtester de estrategias de trading de criptomonedas**, gratuito, de código abierto (GPL-3.0), que corre **100% en la PC del usuario** (Windows).

- Baja datos históricos públicos de **Binance** (spot y futuros perpetuos USDⓈ-M).
- Permite configurar estrategias desde un formulario (sin programar).
- Corre backtests individuales o **cientos/miles de variantes de una misma estrategia en paralelo** (producto cartesiano de parámetros).
- Incluye todas las herramientas de análisis que las plataformas web cobran como "Pro".
- Trae un **asistente (bot) con Gemini** que interpreta resultados en lenguaje simple, ayuda a usar la app y puede lanzar acciones dentro de WICK.

## 2. Para quién

1. **El trader experimentado**: quiere una herramienta rápida, honesta y sin muros de pago.
2. **El principiante**: quiere algo confiable para probar ideas y aprender qué funciona y qué no.
3. **El estafado por gurús**: quiere verificar con datos reales si las estrategias que se venden en internet funcionan. WICK trae esas estrategias típicas precargadas para probarlas en un click.

## 3. Principios no negociables

1. **Honestidad antes que resultados lindos.** El motor simula lo más parecido a la realidad (fees, slippage, funding, liquidación, resolución intra-vela). Si una simplificación favorece al usuario, se elige la opción conservadora y se informa.
2. **Nunca inventar datos.** Si faltan velas, funding o precios de marca, se informa el hueco. No se rellena, no se interpola en silencio, no se generan datos sintéticos (salvo fixtures de tests, marcados como tales).
3. **Sin look-ahead.** Una señal calculada con la vela cerrada `t` se ejecuta recién en la apertura de `t+1`.
4. **El programa calcula, el bot interpreta.** Ninguna cifra que muestre el bot sale del modelo de lenguaje: sale de herramientas del backend.
5. **Reproducible.** El mismo config + los mismos datos + la misma versión del motor = el mismo resultado, bit a bit.
6. **Privacidad.** Sin cuentas, sin telemetría, sin servidores propios. Lo único que sale de la PC: descargas de datos públicos de Binance y los mensajes del chat con el bot (a Google).
7. **Avisos de responsabilidad en todos lados** (ver §9).

## 4. Alcance v1 (lo que SÍ se hace ahora)

### 4.1 Datos
- Exchange único: **Binance**. Mercados: **Spot** y **Futuros perpetuos USDⓈ-M**.
- Catálogo de símbolos desde los endpoints públicos `exchangeInfo`, con buscador.
- Descarga de **velas de 1 minuto** de toda la historia disponible (o rango elegido). Todos los demás timeframes se generan localmente por agregación (resample).
- Timeframes ofrecidos: 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w y 1M. También timeframes custom en minutos (por ejemplo 45m o 90m).
- Para futuros, además: **funding rate histórico** y **velas de precio de marca (mark price) de 1m**.
- **Estimación de peso antes de descargar** ("esto ocupa aprox. X MB") y aviso cuando es mucho.
- **Actualización incremental**: solo se baja lo que falta.
- **Verificación**: checksum SHA-256 de cada archivo y detección de huecos. Reporte de integridad visible por símbolo.
- **Pantalla de gestión de datos**: ver qué hay descargado, cuánto pesa, actualizar, borrar.

### 4.2 Estrategias
- **Editor de estrategia por formulario** (estilo WICK original):
  - Mercado (spot o futuros), símbolo(s), timeframe, rango de fechas, capital inicial.
  - **Indicadores** con sus parámetros.
  - **Reglas de entrada** long y/o short (en spot solo long). Cada regla tiene condiciones (cruces, mayor/menor que, dentro de rango, pendiente, etc.).
  - **Sistema de confirmación ponderada**: cada condición puede ser obligatoria o tener un peso, con un umbral mínimo de puntaje para entrar.
  - **Salidas**: stop loss y take profit (% fijo, múltiplo de ATR o por niveles), trailing stop, salida por tiempo, salida por señal opuesta y break-even.
  - **Gestión de riesgo / tamaño**: % del capital por trade, % de riesgo según distancia al stop, o monto fijo. Interés compuesto sí/no.
  - **Apalancamiento** (solo futuros, opcional).
  - **Costos**: fees maker/taker y slippage, con valores por defecto editables.
- **Cualquier parámetro numérico** (y también el símbolo y el timeframe) puede tener **varios valores**: lista explícita o rango `desde/hasta/paso`.
- **Plantillas**: carpeta de estrategias conocidas precargadas (RSI 30/70, cruce de medias, Bollinger, MACD, breakout de Donchian/Turtle, etc.), cada una con descripción de qué promete y advertencias.
- Guardar, duplicar, renombrar y exportar/importar estrategias (JSON).

### 4.3 Multi-variante (la función estrella)
- La app expande todas las combinaciones (producto cartesiano). Ejemplo: riesgo 1–5% (5) × apalancamiento {3, 5, 10} (3) × EMA {20, 50, 100} (3) = **45 variantes**.
- **Antes de correr** muestra: cantidad de variantes, tiempo estimado (midiendo una corrida de prueba) y espacio estimado.
- **Tope por defecto** de 10.000 variantes, con confirmación explícita para superarlo y tope duro configurable.
- Corre en paralelo usando todos los núcleos, con barra de progreso y posibilidad de cancelar.
- Resultado: tabla ordenable de todas las variantes, **heatmaps de parámetros** (2 parámetros a la vez, el resto fijo) y gráfico de dispersión riesgo/retorno.

### 4.4 Herramientas de análisis ("Pro" gratis)
- **Bar magnifier**: resolución intra-vela con datos de 1m, siempre activa.
- **Métricas completas**: retorno, CAGR, drawdown máximo y duración, Sharpe, Sortino, Calmar, profit factor, win rate, expectancia, trades, exposición, fees pagados, funding pagado/cobrado, liquidaciones, resoluciones ambiguas intra-vela y comparación con buy & hold.
- **Desgloses** por día, semana, mes, trimestre y año: retorno, trades y drawdown de cada período. Incluye un heatmap mensual de retornos.
- **Gráfico de velas** con entradas, salidas, stops, liquidaciones e indicadores superpuestos.
- **Curva de equity y de drawdown**.
- **Lista de trades** completa, filtrable y virtualizada.
- **Robustez**:
  - Out-of-sample: separar un % final del período que no se usó para elegir parámetros.
  - Walk-forward: ventanas móviles de optimización y validación.
  - Monte Carlo: remuestreo de trades (bootstrap) con percentiles de retorno y drawdown.
  - **Deflated Sharpe Ratio**: estima cuánto del resultado de la mejor variante se explica por haber probado N variantes.
- **Comparador**: 2 a 4 backtests o variantes lado a lado (métricas, curvas y desgloses).
- **Historial**: se guardan **todos** los backtests, con buscador, filtros, etiquetas y notas.
- **Exportar** (CSV de trades, CSV de variantes, imagen del gráfico, reporte HTML imprimible a PDF) **solo si el usuario lo pide**. La app lo ofrece, nunca exporta sola.

### 4.5 Bot (asistente WICK)
- Proveedor único en v1: **Google AI Studio (Gemini)**. Modelo por defecto `gemini-3.5-flash-lite`, configurable por texto.
- **Solo habla de WICK y de los datos/backtests del usuario.** Ante temas ajenos, redirige amablemente.
- **Puede**:
  - Explicar resultados en lenguaje simple ("ganó fuerte en marzo y el resto del semestre estuvo neutro o en pérdida").
  - Hacer desgloses amigables por semana o mes y comparar períodos.
  - Comparar cómo se movieron varias cripto en un período (con cifras calculadas por la app).
  - Bajar datos que falten (con confirmación si son pesados).
  - Preparar una estrategia en el formulario a partir de una descripción.
  - Lanzar backtests, **siempre con confirmación del usuario** mediante una tarjeta "Confirmar / Cancelar".
  - Responder cómo usar WICK consultando la **guía de usuario** integrada.
  - Explicar los riesgos de sobreoptimización con los números reales del backtest (variantes probadas, DSR, out-of-sample).
- **No puede**: calcular por su cuenta, inventar cifras, opinar sobre noticias o mercado en vivo, dar señales de inversión, ni operar.
- **Verificador de cifras**: cada número que el bot escribe se contrasta con los resultados de herramientas de la conversación. Si no coincide, se marca "cifra no verificada".
- Conversaciones guardadas localmente.
- **Sin internet o sin cuota**: el bot se desactiva con un mensaje claro y el resto de la app funciona igual.

### 4.6 Instalación y configuración
- **Instalador para Windows** (un `.exe`). Durante la instalación:
  1. Muestra la licencia GPL-3.0 y el aviso de responsabilidad.
  2. Pide la **API key de Google AI Studio**, con instrucciones paso a paso (crear proyecto, crear key, pegarla). Se puede saltear: la app funciona sin bot.
  3. Elige la carpeta de datos (por defecto `%LOCALAPPDATA%\WICK\`).
- Crea un acceso directo. Al abrir WICK se levanta el motor local y se abre la interfaz en el navegador predeterminado. Un ícono en la bandeja del sistema permite abrir la interfaz o cerrar WICK.
- **Configuración** dentro de la app: cambiar o borrar la API key, modelo, fees por defecto, carpeta de datos, tema claro/oscuro, núcleos a usar y topes de variantes.
- Sin internet: funciona todo menos descargar datos nuevos y el bot.

### 4.7 Idioma y licencia
- Interfaz y guía **solo en español** en v1. Todos los textos se centralizan en un archivo para facilitar traducciones futuras.
- **GPL-3.0-or-later**. Repositorio público en GitHub cuando la v1 esté completa y funcional.

## 5. Fuera de alcance v1 (posible futuro, NO implementar)

- Otros exchanges (el diseño deja una interfaz `DataSource` lista, con una sola implementación).
- Otros activos (acciones, forex, etc.).
- Otros proveedores de IA para el bot.
- macOS y Linux.
- Trading en vivo, paper trading y conexión a cuentas de exchange.
- Portafolio multi-activo con capital compartido (en v1, varios símbolos = variantes independientes).
- Estrategias escritas en código por el usuario.
- Futuros COIN-M y opciones.

## 6. Pantallas

1. **Bienvenida / primer uso**: aviso de responsabilidad que hay que aceptar, tour breve y estado de la API key.
2. **Inicio**: últimos backtests, datos descargados, accesos rápidos.
3. **Datos**: buscador de símbolos, descargar, estado de integridad, peso, actualizar y borrar.
4. **Estrategias**: mis estrategias, carpeta de plantillas y editor.
5. **Ejecutar**: resumen previo (variantes, tiempo, espacio y advertencias) y confirmación.
6. **Resultado**: pestañas Resumen · Gráfico · Trades · Desglose · Variantes · Robustez.
7. **Historial**: todos los backtests, con filtros, etiquetas y notas.
8. **Comparador**.
9. **Bot**: panel lateral disponible en todas las pantallas, con contexto de la pantalla actual.
10. **Guía**: guía de usuario navegable (la misma que consulta el bot).
11. **Configuración**.

## 7. Datos que maneja la app

- Velas OHLCV de 1m (spot/futuros), velas de mark price 1m (futuros) y funding rate (futuros).
- Reglas del símbolo: tick size, step size y notional mínimo (de `exchangeInfo`, público).
- **Escalones de apalancamiento y margen de mantenimiento**: el endpoint de Binance que los da (`/fapi/v1/leverageBracket`) requiere cuenta autenticada, así que WICK trae una **tabla incluida en el repo** con fecha de captura, que se actualiza en cada release. La app muestra esa fecha.
- Estrategias, backtests, variantes, trades, curvas, conversaciones del bot y configuración: todo local.

## 8. Privacidad (texto que se muestra al usuario)

> WICK no tiene cuentas, no recolecta datos y no envía nada a servidores propios. Los datos de mercado se descargan de los archivos públicos de Binance. Si usás el asistente, tus mensajes y los resultados que el asistente consulta se envían a Google (Gemini) para generar la respuesta; según el plan de tu API key, Google puede usarlos para mejorar sus servicios. WICK nunca te pide ni maneja datos personales, claves de exchange ni dinero real.

## 9. Avisos de responsabilidad (obligatorios)

- **Primer uso** (aceptación obligatoria): un backtest es una simulación sobre datos pasados. No predice el futuro, no es asesoramiento financiero y no garantiza nada. Operar con apalancamiento puede hacerte perder todo el capital.
- **Banner permanente en cada resultado**: "Resultado sobre datos pasados. No garantiza resultados futuros."
- **Aviso de sobreoptimización contextual**: cuando se corrieron N variantes, se muestra "Probaste N variantes; que la mejor gane es esperable aunque la estrategia no tenga ventaja real", junto con el Deflated Sharpe Ratio y la invitación a validar out-of-sample.
- **Muestra chica**: si hay menos de 30 trades, se avisa que el resultado es estadísticamente débil.
- **Concentración**: si más del 50% de la ganancia sale de un solo mes o de menos del 10% de los trades, se avisa.
- **Edge que desaparece**: si el out-of-sample rinde mucho peor que el in-sample, se avisa.
- **Datos incompletos**: si hay huecos en el rango usado, se muestran en el resultado.
- **Futuros sin mark price** en algún tramo: se avisa que la liquidación se aproximó con el precio last.
- **Plantillas de "estrategias de internet"**: aviso de que se incluyen para verificarlas, no como recomendación.
- Regla general de redacción: **tono claro, sin alarmismo, sin promesas**. Nunca usar palabras como "rentable", "ganadora" o "segura" para describir una estrategia.
