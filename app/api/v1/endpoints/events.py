from fastapi import APIRouter, status, Depends
from sqlalchemy.orm import Session
from app.dependencies import get_db
from app.schemas.event import GameEvent
from app.services import ingestion

router = APIRouter()

@router.post("/events", status_code=status.HTTP_201_CREATED)
async def ingest_event(event: GameEvent, db: Session = Depends(get_db)):
    return await ingestion.ingest_event(event, db)