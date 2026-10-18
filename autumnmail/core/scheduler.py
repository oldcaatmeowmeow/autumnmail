from __future__ import annotations

import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler

from ..store import repo
from .sync import sync_all

logger = logging.getLogger("autumnmail.scheduler")
_scheduler: BackgroundScheduler | None = None


def _run() -> None:
    try:
        settings = repo.get_settings()
        result = sync_all(since_days=settings["scan_since_days"])
        logger.info("scheduled sync: %s", result.get("message"))
    except Exception:
        logger.exception("scheduled sync failed")


def start(interval_min: int = 15) -> BackgroundScheduler:
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    interval = max(1, int(interval_min or 15))
    scheduler = BackgroundScheduler(daemon=True)
    scheduler.add_job(
        _run,
        "interval",
        minutes=interval,
        id="autumnmail-sync",
        replace_existing=True,
        next_run_time=datetime.now() + timedelta(seconds=30),
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    _scheduler = scheduler
    logger.info("scheduler started: every %s minutes", interval)
    return scheduler


def stop() -> None:
    global _scheduler
    if _scheduler is None:
        return
    try:
        _scheduler.shutdown(wait=False)
    except Exception:
        pass
    _scheduler = None
