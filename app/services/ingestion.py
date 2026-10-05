from typing import List

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.event import GameEventModel
from app.schemas.event import GameEvent

logger = get_logger("ingestion")

async def ingest_event(event: GameEvent, db: AsyncSession):
    query = select(GameEventModel).filter(
        GameEventModel.event_id == event.event_id
    )

    exisiting = await db.scalar(query)

    if exisiting:
        return {"message": "Event already exists", "event_id": str(event.event_id)}
    
    db_event = GameEventModel(
        event_id=event.event_id,
        event_type=event.event_type,
        player_id=event.player_id,
        session_id=event.session_id,
        timestamp=event.timestamp,
        event_data=event.metadata.model_dump() if event.metadata else None
    )

    db.add(db_event)
    try:
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        logger.warning(
            "Integrity error while ingesting event",
            extra={"event_id": str(event.event_id), "error": str(e)},
        )
        return {"message": "Event already exists", "event_id": str(event.event_id)}
    
    return {"message": "Event received", "event_id": str(event.event_id)}

async def ingest_batch(events: List[GameEvent], db: AsyncSession):
    ingested = 0
    skipped = 0

    for event in events:
        result = await ingest_event(event, db)
        if result["message"] == "Event already exists":
            skipped += 1
        else:
            ingested += 1
    
    return {"ingested": ingested, "skipped": skipped}

