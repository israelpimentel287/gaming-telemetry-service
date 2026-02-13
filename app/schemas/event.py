from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict
from uuid import UUID
from enum import Enum

class EventType(str, Enum):
    """Allowed event types"""
    PLAYER_MOVE = "player_move"
    SCORE_UPDATE = "score_update"
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    
class EventMetadata(BaseModel):
    score: Optional[int] = None
    position: Optional[Dict[str, float]] = None
    action: Optional[str] = None
    duration_ms: Optional[int] = None

class GameEvent(BaseModel):
    event_id: UUID
    event_type: EventType
    timestamp: datetime
    player_id: str
    session_id: str
    metadata: EventMetadata