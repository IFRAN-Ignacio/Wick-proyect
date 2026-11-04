"""Registro de jobs en memoria (MVP): estado, progreso y resultado.

Los jobs corren en hilos de fondo; los backtests multi-variante además usan un
ProcessPoolExecutor adentro del hilo.
"""

from __future__ import annotations

import threading
import traceback
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Job:
    id: str
    kind: str
    status: str = "running"  # running | done | error
    done: int = 0
    total: int = 0
    message: str = ""
    error: str | None = None
    result: dict[str, Any] = field(default_factory=dict)
    log: list[str] = field(default_factory=list)

    def snapshot(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "status": self.status,
            "done": self.done,
            "total": self.total,
            "message": self.message,
            "error": self.error,
            "result": self.result,
            "log": list(self.log[-50:]),
        }


class JobRegistry:
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()

    def start(self, kind: str, fn: Callable[[Job], dict[str, Any]]) -> Job:
        job = Job(id=uuid.uuid4().hex[:12], kind=kind)
        with self._lock:
            self._jobs[job.id] = job

        def run() -> None:
            try:
                job.result = fn(job)
                job.status = "done"
            except Exception as exc:
                job.error = str(exc) or exc.__class__.__name__
                job.log.append(traceback.format_exc(limit=3))
                job.status = "error"

        threading.Thread(target=run, daemon=True, name=f"job-{job.id}").start()
        return job

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)


registry = JobRegistry()
