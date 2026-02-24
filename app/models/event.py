from sqlalchemy import Column, DateTime, String, Index
from sqlalchemy.dialects.postgresql import UUID
from app.db.database import Base

class GameEventModel(Base):
    __tablename__ = "game_events"
    __table_args__ = (
        Index('ix_game_events_player_timestamp', 'player_id', 'timestamp'),
    )

    event_id = Column(UUID(as_uuid=True), primary_key=True)
    event_type = Column(String, nullable=False)
    player_id = Column(String, nullable=False)
    session_id = Column(String, nullable=False)
    timestamp = Column(DateTime, nullable=False)

