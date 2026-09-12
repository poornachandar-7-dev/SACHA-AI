"""
scheduler/scheduler.py — apscheduler wrapper (AsyncIOScheduler).

Owns the shared scheduler instance, registers ``JobSpec``-driven jobs, and
feeds every execution through the job registry + notifier + execution log.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.base import BaseTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from scheduler.builder import ScheduleSpec
from scheduler.jobs import JobRegistry, JobSpec, Notifier, run_job
from scheduler.log import JobLog
from scheduler.natural_language import parse_reminder, to_job

logger = logging.getLogger(__name__)


class SchedService:
    """Scheduling facade for the HUD + natural-language entries."""

    def __init__(self, notifier: Notifier | None = None, job_log: JobLog | None = None) -> None:
        self.notifier = notifier
        self.job_log = job_log or JobLog()
        self.registry = JobRegistry()
        self._scheduler = AsyncIOScheduler(timezone="local")
        self._jobs_by_spec_id: dict[str, str] = {}  # job_id → apscheduler job id

    async def start(self) -> None:
        self._scheduler.start()
        logger.info("scheduler started")

    async def stop(self) -> None:
        self._scheduler.shutdown(wait=False)
        logger.info("scheduler stopped")

    # -- additions -----------------------------------------------------------
    async def add_schedule(self, spec: ScheduleSpec, job_id: str, title: str) -> str:
        """Register an apscheduler job for an existing JobSpec id."""
        trigger = self._to_trigger(spec)
        aps_id = self._scheduler.add_job(
            self._fire,
            trigger=trigger,
            args=[job_id],
            id=f"job_{job_id}",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        self._jobs_by_spec_id[job_id] = aps_id
        logger.info("scheduled %r: %s", title, spec.human)
        return aps_id

    async def add_job(self, job: JobSpec) -> str:
        self.registry.add(job)
        if job.schedule is not None:
            await self.add_schedule(job.schedule, job.id, job.title)
        return job.id

    async def add_natural(self, text: str) -> JobSpec | None:
        """Add a natural-language reminder; returns None if not a reminder."""
        reminder = parse_reminder(text)
        if reminder is None:
            return None
        job = to_job(reminder)
        await self.add_job(job)
        return job

    # -- execution -------------------------------------------------------------
    async def _fire(self, job_id: str) -> None:
        try:
            job = self.registry.get(job_id)
        except KeyError:
            logger.warning("scheduled fire for unknown job %s", job_id)
            return
        started = datetime.now(UTC)
        status = await run_job(job, self.notifier)
        self.job_log.record(
            job_id=job.id,
            fired_at=started.isoformat(),
            status=status.get("status", "ok"),
            error=status.get("error"),
        )

    # -- tooling -----------------------------------------------------------------
    def list_jobs(self) -> list[dict[str, Any]]:
        return [j.to_dict() for j in self.registry.all()]

    async def remove_job(self, job_id: str) -> None:
        aps_id = self._jobs_by_spec_id.pop(job_id, None)
        if aps_id is not None and self._scheduler.get_job(aps_id):
            self._scheduler.remove_job(aps_id)
        self.registry.remove(job_id)

    def next_runs(self, limit: int = 5) -> list[dict[str, Any]]:
        out = []
        for job in self.registry.all():
            aps_id = self._jobs_by_spec_id.get(job.id)
            if not aps_id:
                continue
            aps_job = self._scheduler.get_job(aps_id)
            if aps_job is None:
                continue
            nxt = self._scheduler.get_job(aps_id).next_run_time
            if nxt:
                out.append({"job_id": job.id, "title": job.title, "next_run": nxt.isoformat()})
        return sorted(out, key=lambda r: r["next_run"])[:limit]

    @staticmethod
    def _to_trigger(spec: ScheduleSpec) -> BaseTrigger:
        if spec.trigger == "interval":
            return IntervalTrigger(**spec.kwargs)
        return CronTrigger(**spec.kwargs)
