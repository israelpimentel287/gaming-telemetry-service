import logging
from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.db.database import SessionLocal
from app.models.event import GameEventModel
from app.models.cohort_stats import CohortStats

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

async def compute_cohort_stats():
    async with SessionLocal() as db:
        try:
            result = await db.execute(
                select(
                    func.avg(GameEventModel.event_data["score"].as_float()),
                    func.stddev(GameEventModel.event_data["score"].as_float())
                ).where(GameEventModel.event_type == "score_update")
            )
            row = result.one()
            mean, stddev = row

            if mean is None or stddev is None:
                logger.warning("Not enough data to compute cohort stats")
                return
            
            stats = CohortStats(mean=float(mean), stddev=float(stddev))
            db.add(stats)
            await db.commit()
            logger.info("Cohort stats saved: mean=%.2f stddev=%.2f", mean, stddev)
        
        except Exception:
            logger.exception("Failed to compute cohort stats")
            await db.rollback()