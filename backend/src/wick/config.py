"""Rutas y settings de WICK.

La carpeta de datos por defecto es `%LOCALAPPDATA%\\WICK` (vía platformdirs).
Se puede cambiar con la variable de entorno `WICK_DATA_DIR` (los tests la usan
para trabajar siempre en un directorio temporal y no tocar datos del usuario).
"""

from __future__ import annotations

import os
from pathlib import Path

from platformdirs import user_data_dir


def data_root() -> Path:
    override = os.environ.get("WICK_DATA_DIR")
    root = Path(override) if override else Path(user_data_dir("WICK", appauthor=False))
    root.mkdir(parents=True, exist_ok=True)
    return root


def market_data_dir() -> Path:
    path = data_root() / "data"
    path.mkdir(parents=True, exist_ok=True)
    return path


def db_path() -> Path:
    return data_root() / "wick.db"


def numba_cache_dir() -> Path:
    path = data_root() / "numba_cache"
    path.mkdir(parents=True, exist_ok=True)
    return path


def frontend_dist_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "frontend" / "dist"
