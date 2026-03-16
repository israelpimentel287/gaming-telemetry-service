from pydantic import BaseModel
from datetime import date, timedelta, datetime
from typing import Dict, Any

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