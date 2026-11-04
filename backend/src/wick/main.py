"""App FastAPI de WICK. En producción sirve el build del frontend (mismo origen, sin CORS)."""

from __future__ import annotations

import os

from wick.config import frontend_dist_dir, numba_cache_dir

# Antes de importar Numba: caché de compilación en la carpeta de datos.
os.environ.setdefault("NUMBA_CACHE_DIR", str(numba_cache_dir()))

from fastapi import APIRouter, FastAPI
from fastapi.staticfiles import StaticFiles

from wick import __version__
from wick.api import backtests, bot, data, errors, jobs, strategies
from wick.api.models import Health
from wick.engine.core import ENGINE_VERSION

app = FastAPI(title="WICK", version=__version__)
errors.install(app)

api = APIRouter(prefix="/api/v1")


@api.get("/health", response_model=Health, tags=["health"])
def health() -> Health:
    return Health(status="ok", version=__version__, engine_version=ENGINE_VERSION)


for _r in (data.router, jobs.router, strategies.router, backtests.router, bot.router):
    api.include_router(_r)
app.include_router(api)

_dist = frontend_dist_dir()
if _dist.exists():
    app.mount("/", StaticFiles(directory=_dist, html=True), name="ui")
