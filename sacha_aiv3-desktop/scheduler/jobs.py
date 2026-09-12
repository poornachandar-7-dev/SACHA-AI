"""
scheduler/jobs.py — built-in job types.

A JobSpec is data; the JobRegistry maps a job's *kind* to an async executor
that receives a notifier callable (the HUD speak/toast hook, telegram
bridge, etc.).
"""

from __future__ import annotations

import asyncio
import logging
import secrets
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from scheduler.builder import ScheduleSpec

logger = logging.getLogger(__name__)

Notifier = Callable[[str], Awaitable[None] | None]


@dataclass
class JobSpec:
    id: str
    title: str
    kind: str  # "say" | "command" | "plugin"
    payload: dict[str, Any] = field(default_factory=dict)
    schedule: ScheduleSpec | None = None
    enabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "kind": self.kind,
            "payload": dict(self.payload),
            "schedule": self.schedule.to_dict() if self.schedule else None,
            "enabled": self.enabled,
        }

    @staticmethod
    def next_id(kind: str) -> str:
        return f"{kind}_{secrets.token_hex(4)}"


async def run_job(job: JobSpec, notifier: Notifier | None = None) -> dict[str, Any]:
    """Execute one job. Returns a status dict for the execution log."""
    status: dict[str, Any] = {"job_id": job.id, "kind": job.kind, "status": "ok"}
    try:
        if job.kind == "say":
            text = job.payload.get("text", job.title)
            if notifier is not None:
                result = notifier(text)
                if asyncio.iscoroutine(result):
                    await result
            logger.info("scheduled say: %s", text)
        elif job.kind == "command":
            import subprocess

            cmd = job.payload.get("command")
            if not cmd:
                raise ValueError("command job missing 'command'")
            proc = await asyncio.create_subprocess_shell(
                cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            await proc.communicate()
            status["exit_code"] = proc.returncode
        elif job.kind == "plugin":
            raise NotImplementedError(f"plugin job execution lands with the plugin host: {job.kind}")
        else:
            raise ValueError(f"unknown job kind {job.kind!r}")
    except Exception as exc:
        logger.warning("job %s failed: %s", job.id, exc)
        status.update({"status": "error", "error": str(exc)})
    return status


class JobRegistry:
    """Name → kind table so callers can auto-run jobs by kind."""

    def __init__(self) -> None:
        self._jobs: dict[str, JobSpec] = {}

    def add(self, job: JobSpec) -> JobSpec:
        self._jobs[job.id] = job
        return job

    def get(self, job_id: str) -> JobSpec:
        return self._jobs[job_id]

    def remove(self, job_id: str) -> None:
        self._jobs.pop(job_id, None)

    def all(self) -> list[JobSpec]:
        return list(self._jobs.values())
