"""Unit tests — scheduler (builder, natural_language, log)."""

from scheduler.builder import parse_expression
from scheduler.log import JobLog
from scheduler.natural_language import parse_reminder, to_job


def test_interval_every_n_minutes():
    spec = parse_expression("every 30 minutes")
    assert spec is not None
    assert spec.trigger == "interval"
    assert spec.kwargs["seconds"] == 1800


def test_interval_every_day():
    spec = parse_expression("every 2 days")
    assert spec.trigger == "interval"
    assert spec.kwargs["seconds"] == 2 * 86400


def test_daily_cron_at_time():
    spec = parse_expression("every day at 08:30")
    assert spec.trigger == "cron"
    assert spec.kwargs == {"hour": 8, "minute": 30}


def test_weekday_cron():
    spec = parse_expression("every monday at 09:00")
    assert spec.trigger == "cron"
    assert spec.kwargs["day_of_week"] == "mon"
    assert spec.kwargs["hour"] == 9


def test_weekend_cron():
    spec = parse_expression("every weekend at 10:00")
    assert spec.kwargs["day_of_week"] == "sat,sun"


def test_morning_word():
    spec = parse_expression("every morning")
    assert spec.trigger == "cron"
    assert spec.kwargs["hour"] == 8


def test_garbage_returns_none():
    assert parse_expression("rgb(12, 34, 56) nonsense") is None


def test_parse_reminder_full_sentence():
    reminder = parse_reminder("remind me to water the plants every morning at 8")
    assert reminder is not None
    assert "water the plants" in reminder.task
    assert reminder.schedule.trigger == "cron"


def test_parse_reminder_rejects_non_reminder():
    assert parse_reminder("what is the weather today") is None


def test_to_job_reuses_task():
    reminder = parse_reminder("remind me to stretch")
    job = to_job(reminder)
    assert job.kind == "say"
    assert "stretch" in job.payload["text"]
    assert job.schedule is not None


def test_job_log_records_and_lists(tmp_path):
    log = JobLog(tmp_path / "jobs.db")
    log.record("job_1", status="ok")
    log.record("job_1", status="error", error="timeout")
    rows = log.last("job_1")
    assert len(rows) == 2
    failures = log.failures()
    assert len(failures) == 1
    assert failures[0]["error"] == "timeout"
    log.close()
