# Manual de usuario de WICK

Versión MVP · noviembre 2026

Este manual explica todo lo que la versión actual de WICK puede hacer y cómo usarla. El asistente integrado de WICK responde dudas de uso a partir de este mismo texto.

---

## 1. Qué es WICK

WICK es un **backtester de estrategias de trading de criptomonedas**. Toma datos históricos reales de Binance y simula cómo le habría ido a una estrategia en el pasado, sin usar plata real.

- Es **gratuito y de código abierto** (licencia GPL-3.0).
- Corre **100% en tu computadora**: no tiene cuentas, no recolecta datos y no tiene servidores propios.
- Lo único que se conecta a internet: la descarga de datos públicos de Binance y, si lo usás, el asistente (Google Gemini).

### Filosofía
WICK prioriza la **honestidad del resultado** por sobre los resultados lindos. El motor cobra comisiones y deslizamiento de precio, compra recién en la vela siguiente a la señal y, cuando hay una duda, elige el supuesto que **perjudica** al usuario. Un resultado de WICK puede ser peor que el de otras plataformas, pero es más parecido a lo que pasaría en la realidad.

**Importante:** un backtest es una simulación sobre el pasado. No predice el futuro, no es asesoramiento financiero y no garantiza nada.

---

## 2. Cómo abrir WICK

1. Abrí **PowerShell**.
2. Escribí:
   ```
   cd C:\dev\wick
   .\dev.ps1
   ```
3. Se abren **dos ventanas** nuevas (el backend y la interfaz) y el navegador en `http://localhost:5173`.
4. **No cierres esas dos ventanas** mientras uses WICK. Si las cerrás, la app deja de funcionar.

Si Windows dice que *la ejecución de scripts está deshabilitada*, usá:
```
powershell -ExecutionPolicy Bypass -File .\dev.ps1
```

**Para cerrar WICK:** cerrá las dos ventanas del backend y la interfaz (o apretá Ctrl+C en cada una).

La primera vez que corrés un backtest puede tardar unos segundos de más: el motor se compila. Después va rápido.

---

## 3. Las pantallas

El menú de la izquierda tiene: **Datos**, **Estrategia**, **Historial**, **Configuración** y el botón **Asistente**. Abajo a la izquierda dice **Horario: UTC**: todas las fechas y horas de WICK están en UTC (hora de Argentina + 3 horas).

### 3.1 Datos

Acá se bajan las velas de Binance (mercado **spot**).

- **Buscar símbolo:** escribí parte del nombre, por ejemplo `BTC` o `ETHUSDT`. La lista muestra los símbolos del catálogo de Binance con su estado (**Operando** o **No opera**).
- **Actualizar catálogo:** vuelve a pedir la lista de símbolos a Binance.
- Elegí un símbolo de la lista. Aparece como **Símbolo elegido**.
- **Timeframe:** el tamaño de cada vela: `1m`, `5m`, `15m`, `1h`, `4h` o `1d`.
- **Desde / Hasta:** el rango de fechas.
- **Descargar:** baja los datos con una barra de progreso.

Qué pasa al descargar:
- Los meses cerrados se bajan de los archivos públicos de Binance y se **verifica el checksum** (que el archivo llegó entero y sin modificaciones).
- El mes en curso se completa desde la API pública de Binance. Aparece como "Mes en curso (se completa en la próxima descarga)".
- Si un mes ya estaba descargado, **no se vuelve a bajar** ("N meses ya estaban descargados").
- Si Binance no tiene velas en algún mes (por ejemplo, antes de que el símbolo existiera), se informa.

**Datos descargados:** abajo está la lista de lo que ya bajaste, con cantidad de **velas**, **tamaño**, **rango** y **huecos**.

**Huecos:** son momentos en que Binance no tiene velas (por ejemplo, caídas por mantenimiento). WICK **los informa y nunca los rellena** con datos inventados. Ejemplo real: BTCUSDT 1h tiene un hueco el 24/03/2023 a las 13:00 UTC.

Dónde se guardan: en `%LOCALAPPDATA%\WICK` (archivos Parquet).

### 3.2 Estrategia

Acá se arma la estrategia y se corre el backtest. Tiene estas secciones:

**Plantillas.** Estrategias conocidas listas para usar. Tocá **Usar** para cargarlas en el formulario:
- **Cruce de EMAs 20/50:** compra cuando la EMA de 20 cruza hacia arriba la EMA de 50 y sale cuando la cruza hacia abajo. Stop del 3%.
- **RSI 30/70:** compra cuando el RSI de 14 cruza hacia arriba 30 (sale de sobreventa) y sale cuando cruza hacia arriba 70. Stop del 5%.

Se incluyen para **verificarlas con datos reales, no como recomendación**.

**Mis estrategias:** el desplegable para cargar una estrategia que guardaste antes.

**General:**
- **Nombre:** cómo se va a llamar la estrategia.
- **Símbolo:** por ejemplo `BTCUSDT`. Tiene que estar descargado en Datos.
- **Timeframe:** tiene que coincidir con el que descargaste.
- **Desde / Hasta:** el período a simular.
- **Capital inicial (USDT):** con cuánta plata (simulada) arranca.

**Indicadores.** Tocá **Agregar indicador**. Cada uno tiene:
- **Nombre (id):** un nombre corto en minúsculas, sin espacios (por ejemplo `ema_rapida`). Se usa en las condiciones.
- **Tipo:** SMA (media simple), EMA (media exponencial), RSI, MACD, Bandas de Bollinger o ATR.
- **Precio:** sobre qué precio se calcula: Apertura, Máximo, Mínimo o Cierre.
- Sus parámetros (ver la tabla de abajo).
- **Quitar** lo elimina.

| Indicador | Parámetros | Qué mide |
|---|---|---|
| SMA | Período | Promedio simple de los últimos N precios |
| EMA | Período | Promedio que le da más peso a los precios recientes |
| RSI | Período | Fuerza del movimiento, de 0 a 100. Menos de 30 se suele llamar sobreventa y más de 70 sobrecompra |
| MACD | Rápida, Lenta, Señal | Diferencia entre dos EMAs, con su línea de señal e histograma |
| Bandas de Bollinger | Período, Desvíos | Media con una banda superior e inferior según la volatilidad |
| ATR | Período | Tamaño promedio de las velas (volatilidad) |

Los indicadores con varias salidas (MACD: línea, señal e histograma; Bollinger: superior, media e inferior) muestran cada salida por separado en las condiciones.

**Condiciones de entrada (long).** Cuándo comprar. Tocá **Agregar condición**. Cada condición tiene:
- **Serie:** un indicador o salida de indicador.
- **Operador:** `cruza hacia arriba`, `cruza hacia abajo`, `mayor que` o `menor que`.
- **Contra:** otra serie o un **Número** (por ejemplo, RSI cruza hacia arriba 30).

Si ponés varias condiciones, tienen que cumplirse **todas a la vez** (AND).

**Señal opuesta.** Condiciones para cerrar la posición, también con AND. En spot no se abren ventas en corto: la señal opuesta **solo sirve para salir**, y solo si activás **Salir por señal opuesta**.

**Salidas:**
- **Stop loss:** `Sin stop`, `% fijo` (con **Distancia (%)**) o `Múltiplo de ATR` (con **Período del ATR** y **Multiplicador**). Ejemplo: ATR de 14 × 2 pone el stop a 2 veces el tamaño promedio de vela por debajo de la entrada.
- **Take profit:** `Sin take profit`, `% fijo` (con **Distancia (%)**) o `Relación riesgo/beneficio` (con **Relación (× el riesgo)**). Ejemplo: relación 2 con stop del 3% pone el take profit a 6% de ganancia. Requiere tener stop.
- **Salir por señal opuesta:** cierra cuando se cumplen las condiciones de la señal opuesta.

**Tamaño:**
- **% de la equity por trade:** qué parte de la plata disponible se usa en cada compra (100 = todo).
- **Interés compuesto:** si está activado, el % se calcula sobre la plata actual (las ganancias y pérdidas se reinvierten). Si está desactivado, se calcula siempre sobre el capital inicial.

**Costos:**
- **Comisión taker (%):** por defecto 0,1% (lo que cobra Binance spot), en cada compra y en cada venta.
- **Slippage (%):** por defecto 0,05%. Es la diferencia entre el precio esperado y el real; siempre se aplica **en contra**.

Los valores por defecto son los de Binance spot al 04/11/2026 y se pueden editar.

**Barra de abajo.** Siempre visible. Muestra:
- La cantidad de **variantes** que vas a correr.
- Cuántas velas hay disponibles en el rango, o el aviso "No hay datos descargados para este símbolo y timeframe" con el botón **Ir a Datos**.
- Avisos de datos (por ejemplo, huecos).
- **Correr backtest** y **Guardar estrategia**.

### 3.3 Multi-variante: probar muchas versiones a la vez

Es la función principal de WICK. Al lado de cada parámetro numérico hay tres modos: **valor**, **lista** y **rango**.

- **valor:** un solo número, por ejemplo `20`.
- **lista:** varios números separados por coma, por ejemplo `10, 20, 30`.
- **rango:** **desde**, **hasta** y **paso**. Por ejemplo, desde 1, hasta 5, paso 1 da 1, 2, 3, 4 y 5.

WICK prueba **todas las combinaciones**. Ejemplo:
- EMA rápida `10, 20, 30` (3 valores)
- EMA lenta `50, 100` (2 valores)
- Stop `2, 4` (2 valores)
- Total: 3 × 2 × 2 = **12 variantes**.

El contador de la barra de abajo se actualiza en vivo. Algunas combinaciones imposibles se descartan y se cuentan ("N combinaciones descartadas"), por ejemplo comparar una EMA consigo misma.

El tope de esta versión es de **2.000 variantes**. Si lo superás, WICK no deja correr y pide que achiques las listas o rangos.

Las variantes corren **en paralelo** usando los núcleos de tu procesador, con una barra de progreso ("N / M variantes").

**Ojo con la sobreoptimización.** Cuantas más variantes probás, más probable es que alguna dé bien **por pura suerte**. WICK te lo recuerda antes de correr y en el resultado: "Vas a probar N variantes: que la mejor gane es esperable aunque la estrategia no tenga ventaja real." Que la mejor de 500 variantes haya ganado no significa que vaya a ganar en el futuro.

### 3.4 Resultado

Arriba siempre aparece el aviso: **"Resultado sobre datos pasados. No garantiza resultados futuros."**

**Variantes** (si corriste más de una): una tabla con todas. Tocá un **encabezado** para ordenar por esa métrica y una **fila** para ver el detalle de esa variante.

**Métricas** de la variante elegida:

| Métrica | Qué significa |
|---|---|
| Retorno total | Cuánto ganó o perdió en total, en %, desde el capital inicial |
| Equity final | Con cuánta plata terminó |
| Máximo drawdown | La peor caída desde un máximo hasta un mínimo. −50% significa que en algún momento llegaste a tener la mitad de lo que habías llegado a tener |
| Win rate | % de trades que terminaron en ganancia |
| Profit factor | Ganancias totales ÷ pérdidas totales. Más de 1 = ganó más de lo que perdió; menos de 1 = perdió más. "∞" si no hubo pérdidas |
| Trades | Cantidad de operaciones cerradas |
| Sharpe (diario, ×√365) | Retorno en relación al riesgo (la variabilidad diaria). Más alto es mejor; cerca de 0 o negativo es malo |
| Fees pagados | Total de comisiones cobradas |
| Trades ambiguos | Veces en que el stop y el take profit se tocaron en la misma vela; se asumió el stop |
| Comprar y mantener | Qué habría pasado si comprabas al inicio y vendías al final sin estrategia. Sirve para comparar |
| Tiempo en el mercado | % del período con una posición abierta |

Las métricas que no aplican (por ejemplo, sin trades) se muestran como "—".

**Avisos** que puede mostrar:
- Sobreoptimización (si corriste varias variantes).
- **Muestra chica:** menos de 30 trades; el resultado es estadísticamente débil.
- Salidas ambiguas.
- Entradas omitidas por no llegar al monto mínimo de Binance.
- Datos incompletos, o que empiezan o terminan fuera del rango pedido.

**Pestañas:**
- **Gráfico:** las velas con flechas de **Compra** y **Venta** en cada trade, más la **Curva de equity** (cómo evolucionó la plata). Si hay muchas velas, el gráfico muestra las últimas y lo avisa. Gráficos por TradingView Lightweight Charts™.
- **Trades:** cada operación con señal, entrada, salida, precios, cantidad, PnL neto, retorno y **motivo** de salida: Señal opuesta, Stop, Take profit o Fin del período. Las ambiguas se marcan.
- **Desglose mensual:** retorno, cantidad de trades y PnL neto de cada mes. Sirve para ver si la estrategia ganó de forma pareja o si todo salió de uno o dos meses buenos.

Al abrir una variante, WICK la **recalcula** ("Recalculando la variante…") con los mismos datos. El resultado es siempre el mismo.

### 3.5 Historial

La lista de todos los backtests que corriste, con **Fecha**, **Estrategia**, **Mercado**, **Rango**, **Variantes**, **Mejor retorno** y **Estado** (Terminado, Corriendo o Error). **Abrir** vuelve a mostrar el resultado. El historial queda guardado aunque cierres WICK.

### 3.6 Configuración

- **API key de Google AI Studio (Gemini):** pegala y tocá **Guardar**. Se guarda en el **Administrador de credenciales de Windows**, no en un archivo. Arriba dice "Hay una API key cargada" o "No hay API key cargada". **Borrar key** la elimina.
- **Modelo:** el modelo de Gemini que usa el asistente. Por defecto `gemini-3.5-flash-lite`. **Guardar modelo** lo cambia.
- Abajo está el texto de privacidad.

### 3.7 Asistente

El botón **Asistente** abre un panel a la derecha. Escribí tu pregunta y tocá **Enviar**. **Cerrar** lo oculta.

---

## 4. Cómo conseguir la API key de Google AI Studio (gratis)

Sin key, WICK funciona igual; solo queda desactivado el asistente.

1. Entrá a **aistudio.google.com** con tu cuenta de Google.
2. Tocá **Get API key**.
3. Tocá **Create API key** y elegí o creá un proyecto.
4. Copiá la key.
5. En WICK, andá a **Configuración**, pegala y tocá **Guardar**.

**No compartas tu key con nadie** ni la publiques: cualquiera que la tenga puede usar tu cuota.

Si la cuota gratuita se agota, el asistente avisa "Se agotó la cuota gratuita de tu API key por ahora" y el resto de WICK sigue funcionando.

---

## 5. Qué hace y qué no hace el asistente

**Puede:**
- Listar tus backtests guardados.
- Explicar un backtest: sus métricas, sus avisos y su configuración.
- Explicar el **desglose mensual**: en qué meses le fue bien o mal, si la ganancia se concentró en pocos meses.
- Responder dudas de **cómo usar WICK** a partir de este manual.
- Explicar qué significa cada métrica o concepto.

**No puede:**
- Calcular números por su cuenta: todas las cifras que da salen de WICK.
- Correr backtests ni bajar datos (en esta versión solo lee).
- Dar recomendaciones de inversión ni predecir precios.
- Hablar de temas que no sean WICK.

Al lado de la respuesta aparece **"Consultó:"** con las herramientas que usó para sacar los datos.

Preguntas de ejemplo:
- "¿Qué backtests tengo?"
- "Explicame el último backtest."
- "¿En qué mes le fue mejor y en cuál peor?"
- "¿Qué es el drawdown?"
- "¿Cómo armo una estrategia con dos EMAs?"
- "¿Cómo pruebo varios stops a la vez?"

---

## 6. Cómo simula el motor (los supuestos)

Saber esto ayuda a interpretar los resultados:

1. **Sin mirar el futuro.** La señal se calcula con la vela ya cerrada y la compra se hace en la **apertura de la vela siguiente**.
2. **Slippage en contra.** Al comprar se paga un poco más que la apertura; al vender se recibe un poco menos.
3. **Comisión en cada operación**, de entrada y de salida. Si usás el 100% del capital, la cantidad comprada se achica para que alcance a pagar la comisión.
4. **Stop y take profit en la misma vela:** como no se sabe cuál se tocó primero, **se asume el stop** (lo peor). Se cuenta como "ambiguo".
5. **Gaps:** si una vela abre por debajo del stop, se vende al precio de apertura (peor que el stop), como pasaría en la realidad.
6. **Fin del período:** si queda una posición abierta, se cierra al precio de cierre de la última vela.
7. **Una posición a la vez**, solo compras (spot). No se usa apalancamiento.
8. **Huecos:** no se inventan velas; el motor salta de una vela real a la siguiente.
9. **Mínimos de Binance:** si un trade no llega al monto mínimo, no se abre y se avisa.

Por todo esto, un resultado de WICK suele ser **más conservador** que el de otras plataformas.

---

## 7. Ejemplo completo paso a paso

1. **Datos:** buscá `BTCUSDT`, elegilo, timeframe `1h`, desde 01/01/2023 hasta 31/12/2025 y tocá **Descargar**.
2. **Estrategia:** en Plantillas, tocá **Usar** en "Cruce de EMAs 20/50".
3. Tocá **Correr backtest**.
4. Mirá el resultado: compará el **Retorno total** con **Comprar y mantener** y revisá el **Desglose mensual**.
5. Volvé a **Estrategia** y cargá la plantilla de nuevo. En el período de la EMA rápida elegí **lista** y escribí `10, 20, 30`; en la EMA lenta, `50, 100`; en la distancia del stop, `2, 4`. La barra tiene que decir **12 variantes**.
6. Corré, y en la tabla de **Variantes** ordená por Retorno total. Tocá una fila para ver su detalle.
7. Abrí el **Asistente** y preguntale: "Explicame el desglose mensual del último backtest".

---

## 8. Preguntas frecuentes

**No me deja correr: dice que no hay datos.** Bajá ese símbolo y **ese mismo timeframe** en Datos. Los datos de 1h no sirven para correr en 4h; hay que bajar 4h aparte.

**El primer backtest tarda.** Es la compilación inicial del motor. Después es rápido.

**¿Por qué mi estrategia da peor que en otra plataforma?** Probablemente porque WICK cobra comisiones y slippage, compra en la vela siguiente y asume lo peor cuando hay ambigüedad.

**La mejor variante ganó mucho. ¿Es buena la estrategia?** No necesariamente. Si probaste muchas variantes, que una gane puede ser suerte. Mirá si el resultado es parecido en variantes vecinas, si hay suficientes trades y si el desglose mensual es parejo. Y siempre: es pasado.

**¿Puedo probar futuros o apalancamiento?** Todavía no; esta versión es solo spot y solo compras.

**¿Puedo cambiar de modelo de IA?** Podés cambiar el modelo de Gemini en Configuración. Otros proveedores de IA no están disponibles en esta versión.

**El asistente dice que no está disponible.** Revisá que haya una key cargada en Configuración y que tengas internet.

**¿Las fechas están en hora argentina?** No, están en UTC. Para pasar a hora argentina, restale 3 horas.

**¿Dónde están mis datos?** En `%LOCALAPPDATA%\WICK`. La API key está en el Administrador de credenciales de Windows.

**¿WICK manda mis datos a algún lado?** No. Solo se conecta a Binance para bajar datos públicos y, si usás el asistente, manda a Google tus mensajes y los resultados que consulta.

---

## 9. Glosario

- **Backtest:** simulación de una estrategia sobre datos pasados.
- **Vela (candle):** el resumen del precio en un período: apertura, máximo, mínimo y cierre.
- **Timeframe:** la duración de cada vela (1 hora, 4 horas, 1 día…).
- **Spot:** compra y venta directa de la cripto, sin apalancamiento.
- **Long:** comprar esperando que el precio suba.
- **Señal:** el momento en que se cumplen las condiciones de la estrategia.
- **Stop loss:** precio al que se vende para cortar la pérdida.
- **Take profit:** precio al que se vende para tomar la ganancia.
- **Slippage:** diferencia entre el precio esperado y el que realmente se consigue.
- **Comisión taker:** lo que cobra el exchange por una orden que se ejecuta al instante.
- **Equity:** la plata total en un momento (efectivo más el valor de la posición abierta).
- **Drawdown:** caída desde un máximo de la equity.
- **Win rate:** porcentaje de trades ganadores.
- **Profit factor:** ganancias ÷ pérdidas.
- **Sharpe:** retorno en relación al riesgo.
- **Variante:** una combinación concreta de parámetros de una estrategia.
- **Sobreoptimización (overfitting):** ajustar tanto una estrategia al pasado que deja de servir en el futuro.
- **Hueco:** período en que no hay datos de Binance.
- **Checksum:** código que verifica que un archivo descargado llegó entero y sin cambios.
- **UTC:** horario universal (Argentina es UTC−3).
- **API key:** clave personal para usar un servicio, en este caso Gemini.
