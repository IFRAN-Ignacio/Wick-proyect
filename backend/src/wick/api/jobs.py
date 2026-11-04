from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from wick.api.models import JobOut
from wick.jobs.registry import registry

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: str) -> JobOut:
    job = registry.get(job_id)
    if job is None:
        raise KeyError("No existe ese job.")
    return JobOut.model_validate(job.snapshot())


@router.get("/{job_id}/events")
async def job_events(job_id: str) -> StreamingResponse:
    """SSE de progreso: un evento por cambio; el último tiene status done o error."""
    job = registry.get(job_id)
    if job is None:
        raise KeyError("No existe ese job.")

    async def stream() -> AsyncIterator[str]:
        last = ""
        while True:
            snap = json.dumps(job.snapshot())
            if snap != last:
                last = snap
                yield f"data: {snap}\n\n"
            if job.status != "running":
                break
            await asyncio.sleep(0.3)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
