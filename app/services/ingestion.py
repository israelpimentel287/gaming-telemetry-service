from app.schemas.event import GameEvent
from sqlalchemy.orm import Session
from app.models.event import GameEventModel

async def ingest_event(event: GameEvent, db: Session):
    exisiting = db.query(GameEventModel).filter(
        GameEventModel.event_id == event.event_id
    ).first()

    if exisiting:
        return {"message": "Event already exists", "event_id": str(event.event_id)}
    
    db_event = GameEventModel(
        event_id=event.event_id,
        event_type=event.event_type,
        player_id=event.player_id,
        session_id=event.session_id,
        timestamp=event.timestamp
    )

    db.add(db_event)
    db.commit()

    return {"message": "Event received", "event_id": str(event.event_id)}