"""Los tests NUNCA usan la carpeta de datos del usuario: todo va a un directorio temporal."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="wick-tests-"))
os.environ["WICK_DATA_DIR"] = str(_TMP)
os.environ.setdefault("NUMBA_CACHE_DIR", str(_TMP / "numba_cache"))
