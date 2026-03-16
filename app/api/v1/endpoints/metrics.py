from fastapi import APIRouter, status, Depends, HTTPException
from datetime import date, datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.dependencies import get_db
from app.schemas.metric import DAUResponse, EBTResponse, PercentileResponse, FlaggedResponse, PRSResponse
from app.services.aggregation import get_dau, get_events_by_type, get_percentile_per_session, get_flagged_player, player_risk_score
import re
from typing import Optional


router = APIRouter(prefix="/metrics")

@router.get("/dau", response_model=list[DAUResponse])
def read_dau(
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db)
):
    return get_dau(db, start_date, end_date)


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
def read_ebt(
    window: str,
    db: Session = Depends(get_db)
):  
    try:
        cutoff_datetime = parse_window(window)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str((e)))

    return get_events_by_type(db, cutoff_datetime)

@router.get("/session-length", response_model=list[PercentileResponse])
def percentage_per_session(
    percentiles: str,
    db: Session = Depends(get_db)
):  
    try:
        percentile_list = [int(p) for p in percentiles.split(",")]
    except ValueError:
            raise HTTPException(status_code=400, detail="Percentiles must be integers seperated by commas")

    results = get_percentile_per_session(db, percentile_list)
    
    return results

@router.get("/flagged-players", response_model=list [FlaggedResponse])
def flagged_player(
    severity: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    return get_flagged_player(db, severity, limit)

@router.get("/player-risk-score/{player_id}", response_model=PRSResponse)
def get_score(
    player_id: int,
    db: Session = Depends(get_db)
):
    score = player_risk_score(db, player_id)

    if score is None:
        raise HTTPException(status_code=404, detail=f"Player {player_id} does not have any flags or was not found")
    
    return score
