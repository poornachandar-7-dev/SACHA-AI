"""
scheduler/builder.py — parses minute/hourly/daily/weekly/cron expressions.

Turns human schedule phrases into :class:`ScheduleSpec` objects that map
onto apscheduler triggers (interval / cron / date).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Literal

TriggerType = Literal["interval", "cron", "date"]

_DAY_NAMES = {
    "monday": "mon", "tuesday": "tue", "wednesday": "wed", "thursday": "thu",
    "friday": "fri", "saturday": "sat", "sunday": "sun",
}

_INTERVAL_RE = re.compile(r"every\s+(\d+)\s+(second|minute|hour|day|week)s?", re.IGNORECASE)
_DAILY_AT_RE = re.compile(r"(?:every\s+)?day\s+at\s+(\d{1,2}):(\d{2})", re.IGNORECASE)
_WEEKDAY_AT_RE = re.compile(r"(?:every\s+)?(monday|tuesday|wednesday|thursday|friday|saturday|sunday|weekday|weekend)s?\s+at\s+(\d{1,2}):(\d{2})", re.IGNORECASE)
_AT_RE = re.compile(r"at\s+(\d{1,2}):(\d{2})", re.IGNORECASE)
_MORNING_RE = re.compile(r"every\s+(morning|afternoon|evening|night)", re.IGNORECASE)


@dataclass
class ScheduleSpec:
    trigger: TriggerType
    kwargs: dict[str, Any]
    human: str

    def to_dict(self) -> dict[str, Any]:
        return {"trigger": self.trigger, "kwargs": dict(self.kwargs), "human": self.human}


def parse_expression(text: str) -> ScheduleSpec | None:
    """Parse a schedule phrase; None when nothing recognizable was found."""
    t = text.strip()
    if not t:
        return None

    # every N seconds/minutes/hours/days/weeks  → interval
    m = _INTERVAL_RE.match(t)
    if m:
        amount = int(m.group(1))
        unit = m.group(2).lower()
        seconds = {"second": 1, "minute": 60, "hour": 3600, "day": 86400, "week": 604800}[unit]
        return ScheduleSpec("interval", {"seconds": amount * seconds}, t)

    # every morning / afternoon / evening / night → cron hour
    m = _MORNING_RE.match(t)
    if m:
        hour = {"morning": 8, "afternoon": 13, "evening": 18, "night": 22}[m.group(1).lower()]
        return ScheduleSpec("cron", {"hour": hour, "minute": 0}, t)

    # every <weekday>/weekday/weekend at HH:MM → cron
    m = _WEEKDAY_AT_RE.match(t)
    if m:
        day = m.group(1).lower()
        dow = "mon-fri" if day == "weekday" else "sat,sun" if day == "weekend" else _DAY_NAMES[day]
        return ScheduleSpec(
            "cron", {"day_of_week": dow, "hour": int(m.group(2)), "minute": int(m.group(3))}, t
        )

    # every day at HH:MM → cron
    m = _DAILY_AT_RE.match(t)
    if m:
        return ScheduleSpec("cron", {"hour": int(m.group(1)), "minute": int(m.group(2))}, t)

    # bare "at HH:MM" → daily cron
    m = _AT_RE.search(t)
    if m:
        return ScheduleSpec("cron", {"hour": int(m.group(1)), "minute": int(m.group(2))}, t)

    # "hourly" / "daily"/ "weekly" shortcut words
    if t.lower() in ("hourly",):
        return ScheduleSpec("interval", {"seconds": 3600}, t)
    if t.lower() in ("daily",):
        return ScheduleSpec("interval", {"seconds": 86400}, t)
    if t.lower() in ("weekly",):
        return ScheduleSpec("interval", {"seconds": 604800}, t)

    return None
