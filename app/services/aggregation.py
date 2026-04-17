from sqlalchemy.orm import Session
from sqlalchemy import func, distinct
from app.models.event import GameEventModel
from app.models.player_flag import Playerflag
from app.schemas.metric import DAUResponse, EBTResponse, PercentileResponse, FlaggedResponse, PRSResponse
from typing import Optional

def get_dau(db: Session, start_date, end_date) -> list[DAUResponse]:

    active_players = (
        db.query(
            func.count(distinct(GameEventModel.player_id)), 
            func.date((GameEventModel.timestamp)
        ))
        .filter(GameEventModel.timestamp.between(start_date, end_date))
        .group_by(func.date(GameEventModel.timestamp))
    )

    results = active_players.all()

    return[
        DAUResponse(
            daily_active_users=row[0],
            date=row[1]
        )for row in results
    ]

def get_events_by_type(db: Session, cutoff) -> list[EBTResponse]:

    results = (
        db.query(
            GameEventModel.event_type,
            func.count(GameEventModel.event_id)
        )
        .filter(GameEventModel.timestamp >= cutoff)
        .group_by(GameEventModel.event_type)
        .all()
    )

    return[
        EBTResponse(
            event=row[0],
            count=row[1]
        )for row in results
    ]

def get_percentile_per_session(db: Session, percentiles:list[int]) -> list[PercentileResponse]:
    sessions = (
        db.query(
            (func.max(GameEventModel.timestamp) - func.min(GameEventModel.timestamp)).label("duration")
        ).group_by(GameEventModel.session_id)
    ).subquery()

    results = []

    for p in percentiles:
        duration = (
            db.query(
                func.percentile_cont(p / 100).within_group(sessions.c.duration)
            )
            .select_from(sessions)
            .scalar()
        )

        results.append(
            PercentileResponse(
                percentile=p,
                duration=duration
            )
        )
    
    return results

def get_flagged_player(db: Session, severity : Optional[str] = None , limit: int = 100) -> list[FlaggedResponse]:
    flagged = db.query(Playerflag)

    if severity is not None:
        flagged = flagged.filter(Playerflag.severity == severity)
    
    results = flagged.limit(limit).all()

    return [
        FlaggedResponse(
            player_id=row.player_id,
            flag_type=row.flag_type,
            severity=row.severity,
            status=row.status,
            context=row.context,
            timestamp=row.timestamp 
        )for row in results 
    ]

def player_risk_score(db: Session,  player_id) -> Optional[PRSResponse]:
    player_flagged = db.query(
        Playerflag.flag_type,
        Playerflag.severity,
        Playerflag.timestamp
        ).filter(Playerflag.player_id == player_id)
    
    results = player_flagged.all()
    
    if not results:
        return None
    
    risks = {
        "low": 1/3,
        "medium": 2/3,
        "high": 3/3,
        "critical": 4/3
    }
    
    total = 0
    for row in results:
        risk_score = risks.get(row.severity, 0)
        total += risk_score
    risk_score = total / len(results)

    all_flags = [r.flag_type for r in results]

    lastest_timestamp = max(row.timestamp for row in results)

    return PRSResponse(
            player_id=player_id,
            risk_score=risk_score,
            flag_type=all_flags,
            timestamp=lastest_timestamp
        )
    