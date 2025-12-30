"""Scheduler pour scans automatiques."""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import logging

from app.config import get_config
from app.core.planner import Planner

logger = logging.getLogger(__name__)

scheduler = None


def start_scheduler():
    """Démarre le scheduler si configuré."""
    global scheduler
    config = get_config()

    if not config.scheduler.enabled:
        logger.info("Scheduler is disabled")
        return

    scheduler = AsyncIOScheduler()

    # Parse cadence
    cadence = config.scheduler.cadence.lower()
    timezone = config.scheduler.timezone

    if "day" in cadence or "jour" in cadence:
        # Daily
        scheduler.add_job(
            run_scheduled_scan,
            trigger=CronTrigger(hour=2, minute=0, timezone=timezone),
            id="daily_scan",
            replace_existing=True,
        )
    elif "hour" in cadence or "heure" in cadence:
        # Hourly
        scheduler.add_job(
            run_scheduled_scan,
            trigger=IntervalTrigger(hours=1),
            id="hourly_scan",
            replace_existing=True,
        )
    else:
        # Default: daily at 2 AM
        scheduler.add_job(
            run_scheduled_scan,
            trigger=CronTrigger(hour=2, minute=0, timezone=timezone),
            id="daily_scan",
            replace_existing=True,
        )

    scheduler.start()
    logger.info(f"Scheduler started with cadence: {cadence}, timezone: {timezone}")


async def run_scheduled_scan():
    """Exécute un scan planifié."""
    logger.info("Running scheduled scan")
    try:
        planner = Planner()
        plan_id = await planner.generate_plan()
        logger.info(f"Scheduled scan completed, plan_id: {plan_id}")
    except Exception as e:
        logger.error(f"Error in scheduled scan: {str(e)}")


def stop_scheduler():
    """Arrête le scheduler."""
    global scheduler
    if scheduler:
        scheduler.shutdown()
        scheduler = None
        logger.info("Scheduler stopped")

