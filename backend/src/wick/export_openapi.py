"""Escribe el OpenAPI de la app a un archivo (lo usa `npm run gen:api`)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from wick.main import app


def main() -> None:
    out = Path(sys.argv[1])
    out.write_text(json.dumps(app.openapi(), indent=1, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
