from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, distinct, select
from app.models.event import GameEventModel
from app.models.player_flag import Playerflag
from app.schemas.metric import DAUResponse, EBTResponse, PercentileResponse, FlaggedResponse, PRSResponse, PaginatedFlaggedResponse
from typing import Optional
from datetime import datetime, timedelta
from app.core.logging import get_logger

logger = get_logger("aggregation")

async def get_dau(db: AsyncSession, start_date, end_date) -> list[DAUResponse]:

    active_players = (
        select(
            func.count(distinct(GameEventModel.player_id)), 
            func.date((GameEventModel.timestamp)
        ))
        .filter(GameEventModel.timestamp.between(start_date, end_date))
        .group_by(func.date(GameEventModel.timestamp))
    )

    result = await db.execute(active_players)
    results = result.all()

    return[
        DAUResponse(
            daily_active_users=row[0],
            date=row[1]
        )for row in results
    ]

async def get_events_by_type(db: AsyncSession, cutoff) -> list[EBTResponse]:

    events = (
        select(
            GameEventModel.event_type,
            func.count(GameEventModel.event_id)
        )
        .filter(GameEventModel.timestamp >= cutoff)
        .group_by(GameEventModel.event_type)
    )

    result = await db.execute(events)
    results = result.all()


    return[
        EBTResponse(
            event=row[0],
            count=row[1]
        )for row in results
    ]

async def get_percentile_per_session(db: AsyncSession, percentiles:list[int]) -> list[PercentileResponse]:
    sessions = (
        select(
            (func.max(GameEventModel.timestamp) - func.min(GameEventModel.timestamp)).label("duration")
        ).group_by(GameEventModel.session_id)
    ).subquery()

    results = []

    for p in percentiles:
        duration = (
            select(
                    func.percentile_cont(p / 100).within_group(sessions.c.duration)
            )
            .select_from(sessions)
        
        )

        duration = await db.scalar(duration) or timedelta(0)

        results.append(
            PercentileResponse(
                percentile=p,
                duration=duration
            )
        )
    
    return results

async def get_flagged_player(db: AsyncSession, cursor: Optional[datetime] = None, severity : Optional[str] = None , limit: int = 100) -> PaginatedFlaggedResponse:

    flagged = select(Playerflag)

    if severity is not None:
        flagged = flagged.filter(Playerflag.severity == severity)
    
    if cursor is not None:
        flagged = flagged.filter(Playerflag.timestamp < cursor)

    results = (
        flagged.order_by(Playerflag.timestamp.desc())
        .limit(limit)
    )

    result = await db.execute(results)
    results = result.scalars().all()

    items = [FlaggedResponse.from_orm(row) for row in results]
    next_cursor = items[-1].timestamp if results else None
    
    return PaginatedFlaggedResponse( items=items, next_cursor=next_cursor)


async def player_risk_score(db: AsyncSession,  player_id) -> Optional[PRSResponse]:
    player_flagged = select(
        Playerflag.flag_type,
        Playerflag.severity,
        Playerflag.timestamp
        ).filter(Playerflag.player_id == player_id)
    
    result = await db.execute(player_flagged)
    results = result.all()
    
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
    