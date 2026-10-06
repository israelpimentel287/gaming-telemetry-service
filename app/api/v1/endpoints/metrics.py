import re
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.dependencies import get_db
from app.schemas.metric import (
    DAUResponse,
    EBTResponse,
    FlaggedResponse,
    PaginatedFlaggedResponse,
    PercentileResponse,
    PRSResponse,
)
from app.services.aggregation import (
    get_dau,
    get_events_by_type,
    get_flagged_player,
    get_percentile_per_session,
    player_risk_score,
)

logger = get_logger("metrics")


router = APIRouter(prefix="/metrics")

@router.get("/dau", response_model=list[DAUResponse])
async def read_dau(
    start_date: date,
    end_date: date,
    db: AsyncSession = Depends(get_db)
):
    return await get_dau(db, start_date, end_date)


def parse_window(value: str):

    match = re.fullmatch(r"(\d+)([a-zA-Z])", value.lower())

    if match:
        number = int(match.group(1))
        unit = match.group(2)
    else:
        raise ValueError("Invalid window")


    unit_map = {
        "s": "seconds",
        "m": "minutes",
        "h": "hours",
        "d": "days"
    }

    if unit not in unit_map:
        raise ValueError("Unsupported time unit")

    cutoff_delta = timedelta(**{unit_map[unit]: number})

    return datetime.now(timezone.utc) - cutoff_delta

@router.get("/events-by-type", response_model=list[EBTResponse])
async def read_ebt(
    window: str,
    db: AsyncSession = Depends(get_db)
):  
    try:
        cutoff_datetime = parse_window(window)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str((e)))

    return await get_events_by_type(db, cutoff_datetime)

@router.get("/session-length", response_model=list[PercentileResponse])
async def percentage_per_session(
    percentiles: str,
    db: AsyncSession = Depends(get_db)
):  
    try:
        percentile_list = [int(p) for p in percentiles.split(",")]
    except ValueError:
            raise HTTPException(status_code=400, detail="Percentiles must be integers seperated by commas")

    results = await get_percentile_per_session(db, percentile_list)
    
    return results

@router.get("/flagged-players", response_model=PaginatedFlaggedResponse)
async def flagged_player(
    cursor_timestamp: Optional[datetime] = None,
    cursor_flag_id: Optional[int] = None,
    severity: Optional[str] = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):

    if (cursor_timestamp is None) != (cursor_flag_id is None):
        raise HTTPException(
            status_code=400,
            detail="cursor_timestamp and cursor_flag_id must be provided together",
        )
    
    return await get_flagged_player(db, cursor_timestamp, cursor_flag_id, severity, limit)

@router.get("/player-risk-score/{player_id}", response_model=PRSResponse)
async def get_score(
    player_id: str,
    db: AsyncSession = Depends(get_db)
):
    score = await player_risk_score(db, player_id)

    if score is None:
        raise HTTPException(status_code=404, detail=f"Player {player_id} does not have any flags or was not found")
    
    return score
