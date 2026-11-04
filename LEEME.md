# Paquete de arranque de WICK

| Archivo | Para qué |
|---|---|
| `PROMPT_INICIAL.md` | Lo que le pegás a Claude Code (más los prompts de fase, cierre y rescate) |
| `CLAUDE.md` | Reglas permanentes; va en la raíz del repo y Claude Code lo lee solo |
| `docs/01_ESPECIFICACION.md` | Qué es WICK, alcance v1, fuera de alcance, pantallas, avisos |
| `docs/02_STACK.md` | Cada tecnología y por qué (y qué se descartó) |
| `docs/03_ARQUITECTURA.md` | Diagramas, módulos, flujos, base de datos, API, esquema de estrategia |
| `docs/04_PSEUDOCODIGO.md` | Ingesta, resample, variantes, señales, motor, métricas, robustez, bot |
| `docs/05_PLAN_DE_FASES.md` | Fases 0–7 con criterios de "hecho" y los tests obligatorios del motor |

Pasos: copiar todo a la carpeta del proyecto → `git init` + commit → abrir Claude Code → pegar `PROMPT_INICIAL.md`.
