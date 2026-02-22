# apps/api/src/scheduler/jobs.py
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from src.config import get_settings
from src.database import SessionLocal
from src.providers import TheOddsApiProvider
from src.services import OddsIngestionService

logger = logging.getLogger(__name__)
settings = get_settings()

scheduler = AsyncIOScheduler()


async def scheduled_ingest():
    """Run odds ingestion. Called every 10 minutes."""
    logger.info("Starting scheduled odds ingestion")

    if not settings.odds_api_key:
        logger.warning("ODDS_API_KEY not set, skipping ingestion")
        return

    db = SessionLocal()
    try:
        provider = TheOddsApiProvider(settings.odds_api_key)
        service = OddsIngestionService(provider, db)
        result = await service.ingest()
        logger.info(f"Ingestion complete: {result.games_processed} games, {result.snapshots_created} snapshots")
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
    finally:
        db.close()


def setup_scheduler():
    """Called on app startup."""
    # Run immediately on startup, then every 10 minutes
    scheduler.add_job(
        scheduled_ingest,
        trigger=IntervalTrigger(minutes=10),
        id="odds_ingestion",
        replace_existing=True,
        max_instances=1,
        next_run_time=datetime.now(),  # Run immediately on startup
    )
    scheduler.start()
    logger.info("Scheduler started - running immediate ingestion, then every 10 minutes")


def shutdown_scheduler():
    """Called on app shutdown."""
    scheduler.shutdown(wait=True)
    logger.info("Scheduler stopped")
