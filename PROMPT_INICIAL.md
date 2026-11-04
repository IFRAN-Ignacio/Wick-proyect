# Prompt inicial para Claude Code

> **Cómo usarlo:**
> 1. Creá la carpeta del proyecto (por ejemplo `C:\dev\wick\`) y copiá adentro `CLAUDE.md` y la carpeta `docs/` tal cual.
> 2. `git init` en esa carpeta y un primer commit con esos archivos.
> 3. Abrí Claude Code en esa carpeta y pegá el texto de abajo (desde "Hola" hasta el final).
> 4. Para cada fase siguiente usá el **prompt de fase** del final de este archivo.

---

Hola. Vamos a construir **WICK** desde cero: un backtester de cripto gratuito, open source (GPL-3.0) y 100% local para Windows, con interfaz en React y un asistente con Gemini.

Todo el diseño ya está cerrado y escrito. Antes de escribir una sola línea de código:

1. Leé **completos**, en este orden: `CLAUDE.md`, `docs/01_ESPECIFICACION.md`, `docs/02_STACK.md`, `docs/03_ARQUITECTURA.md`, `docs/04_PSEUDOCODIGO.md` y `docs/05_PLAN_DE_FASES.md`.
2. Devolveme:
   - Un resumen de 10 líneas o menos de lo que entendiste que es WICK, para confirmar que estamos alineados.
   - **Contradicciones, huecos o ambigüedades** que encuentres entre los documentos, con la cita exacta de cada lado. Quiero esto especialmente: es mejor encontrarlo ahora que en la fase 3.
   - Riesgos técnicos que veas (por ejemplo, algo de Numba en Windows, PyInstaller, límites de Binance), cada uno con la mitigación que propondrías.
   - Qué verificarías primero contra la realidad (por ejemplo, una URL de `data.binance.vision`, la versión de una librería) antes de confiar en lo que dicen los docs.
3. **No escribas código todavía.** Esperá mi respuesta a todo eso.

Cuando te dé el OK, arrancamos con la **Fase 0**: me proponés los bloques de la fase, los apruebo y vamos bloque por bloque, como dice `CLAUDE.md`.

Recordatorios que más me importan:
- Nunca inventes datos ni digas que algo funciona sin haberlo corrido.
- El motor tiene que ser honesto: ante la duda, el supuesto que perjudica al usuario.
- No te salgas del alcance ni agregues dependencias sin preguntar.
- Al final de cada bloque, dame pasos concretos de verificación manual.

---

## Prompt de fase (para usar al empezar cada fase)

```
Cerramos la Fase N-1 (tag fase-N-1). Arrancamos la Fase N de docs/05_PLAN_DE_FASES.md.

1. Releé la sección de la Fase N y las partes de 03_ARQUITECTURA y 04_PSEUDOCODIGO que le correspondan.
2. Proponé la lista de bloques (½–1 día cada uno), con qué entrega cada bloque y cómo se verifica.
3. Señalá cualquier cosa de fases anteriores que haya que ajustar para esta fase.
4. Esperá mi OK antes de codear.
```

## Prompt de cierre de bloque (si Claude Code se olvida del formato)

```
Antes de seguir, dame el cierre del bloque según CLAUDE.md:
qué hiciste, comandos corridos con su salida real, pasos de verificación manual para mí, y riesgos o pendientes.
```

## Prompt de rescate (si ves que se va por las ramas)

```
Pará. Releé CLAUDE.md, reglas de oro y "Forma de trabajar".
Decime en 3 líneas qué estabas haciendo, si está dentro del bloque aprobado y si inventaste o asumiste algo sin verificar.
No sigas hasta que te responda.
```
