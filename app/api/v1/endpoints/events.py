from fastapi import APIRouter, status, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_db
from app.schemas.event import GameEvent
from app.services.fraud_service import FraudDetectionService
from app.services import ingestion
from typing import List
from app.core.logging import get_logger

logger = get_logger("events")

router = APIRouter()

fraud_service = FraudDetectionService()

@router.post("/events", status_code=status.HTTP_201_CREATED)
async def ingest_event(event: GameEvent, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    background_tasks.add_task(fraud_service.analyze_event, event)
    return await ingestion.ingest_event(event, db)

@router.post("/events/batch")
async def ingest_batch(events: List[GameEvent], background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    for event in events:
        background_tasks.add_task(fraud_service.analyze_event, event)
    return await ingestion.ingest_batch(events, db)