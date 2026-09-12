"""
scheduler/natural_language.py — "remind me every morning at 8" → a JobSpec.

The reminder parser extracts both halves of a reminder sentence: *what to
do* and *when*. It composes a :class:`JobSpec` ready for the scheduler.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from scheduler.builder import ScheduleSpec, parse_expression
from scheduler.jobs import JobSpec

_REMIND_RE = re.compile(
    r"(?:remind\s+me|remember)\s+(?:to\s+|about\s+|that\s+)?(.+?)(?:\s*(?:every|at|tomorrow|today|in)\s+.+)?$",
    re.IGNORECASE,
)


@dataclass
class ReminderSpec:
    task: str
    schedule: ScheduleSpec
    raw: str


def parse_reminder(text: str) -> ReminderSpec | None:
    """Parse a reminder sentence. Returns None when it isn't a reminder."""
    lowered = text.strip().lower()
    if not lowered.startswith(("remind me", "remember")):
        return None
    match = _REMIND_RE.match(text.strip())
    task = match.group(1).strip() if match else ""
    if not task or len(task) > 200:
        task = text.strip()

    # Look for the when-part anywhere in the sentence.
    when = ""
    for marker in ("every", "at", "tomorrow", "today", "in "):
        idx = lowered.find(marker)
        if marker == "at" and " at " not in f" {lowered} ":
            continue
        if idx >= 0:
            when = text.strip()[idx:]
            break

    schedule = parse_expression(when) if when else ScheduleSpec("cron", {"hour": 9, "minute": 0}, "daily at 09:00")
    return ReminderSpec(task=task, schedule=schedule, raw=text.strip())


def to_job(reminder: ReminderSpec) -> JobSpec:
    """Build a JobSpec ("say" job that surfaces the reminder via notifier)."""
    return JobSpec(
        id=JobSpec.next_id("reminder"),
        title=reminder.task,
        kind="say",
        payload={"text": f"Reminder: {reminder.task}"},
        schedule=reminder.schedule,
    )
