from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter

from wick.api.models import CatalogOut, DatasetOut, DownloadIn, JobStarted, SymbolOut
from wick.data import catalog
from wick.jobs.registry import registry
from wick.services import data_service

router = APIRouter(prefix="/data", tags=["data"])


@router.get("/catalog", response_model=CatalogOut)
def get_catalog(q: str = "", refresh: bool = False, limit: int = 50) -> CatalogOut:
    symbols, fetched_at = catalog.load_catalog(data_service.source(), refresh=refresh)
    hits = catalog.search(symbols, q, limit=min(limit, 500))
    return CatalogOut(
        fetched_at=fetched_at,
        total=len(symbols),
        symbols=[SymbolOut(**asdict(s)) for s in hits],
    )


@router.post("/download", response_model=JobStarted)
def post_download(body: DownloadIn) -> JobStarted:
    job = registry.start(
        "download",
        lambda job: data_service.download(body.symbol, body.timeframe, body.from_, body.to, job),
    )
    return JobStarted(job_id=job.id)


@router.get("/datasets", response_model=list[DatasetOut])
def get_datasets() -> list[DatasetOut]:
    return [DatasetOut.model_validate(d) for d in data_service.list_datasets()]
