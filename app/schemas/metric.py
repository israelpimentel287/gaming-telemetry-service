from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class DAUResponse(BaseModel):
    date: date
    daily_active_users: int

class EBTResponse(BaseModel):
    event: str
    count: int

class PercentileResponse(BaseModel):
    percentile: int
    duration: timedelta

class FlaggedResponse(BaseModel):
    model_config = {"from_attributes": True}
    
    player_id: str
    flag_type: str
    severity: str
    status: str
    context: Dict[str, Any]
    timestamp: datetime

class PRSResponse(BaseModel):
    player_id: str
    risk_score: float
    flag_type: list[str]
    timestamp: datetime

class PaginatedFlaggedResponse(BaseModel):
    items: List[FlaggedResponse]
    next_cursor_timestamp: Optional[datetime]
    next_cursor_flag_id: Optional[int]