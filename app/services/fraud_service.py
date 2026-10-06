import statistics
from datetime import datetime, timedelta, timezone
from typing import Sequence

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.database import SessionLocal
from app.models.event import GameEventModel
from app.models.player_flag import Playerflag
from app.schemas.event import GameEvent

logger = get_logger("fraud_service")
ANALYZED_EVENTS = {"player_move", "score_update", "session_end"}

class FraudDetectionService:

    async def analyze_event(self, event: GameEvent)-> None:

        if event.event_type not in ANALYZED_EVENTS:
            return
        
        async with SessionLocal() as db:
        
            try:
                if event.event_type == "player_move":
                    if event.metadata.position is None:
                        return
                    
                    previous_move = (
                        select(GameEventModel)
                        .where(
                            GameEventModel.player_id == event.player_id,
                            GameEventModel.session_id == event.session_id,
                            GameEventModel.event_type == "player_move",
                            GameEventModel.timestamp < event.timestamp
                        )
                        .order_by(desc(GameEventModel.timestamp))
                        .limit(1)
                    )

                    previous_move = await db.scalar(previous_move)

                    if previous_move:
                        is_hack, speed = self._check_impossible_movement(event, previous_move)

                        if speed is not None and is_hack:

                            severity = "medium"
                            
                            if 1000 <= speed < 5000:
                                severity = "high"
                            elif speed >= 5000 :
                                severity = "critical"

                            await self._create_flag(
                                db,
                                player_id = event.player_id,
                                flag_type = "speed_hack",
                                severity = severity,
                                context = {
                                    "session_id": event.session_id,
                                    "event_id": str(event.event_id),
                                    "speed": speed
                                }
                            )
                            logger.warning("FLAG: Player %s suspected of speed hacking", event.player_id)
                        elif speed is not None:
                            logger.info("Player %s moved at %.2f units/sec", event.player_id, speed)

                    cutoff = event.timestamp - timedelta(seconds=30)

                    recent_events = (
                        select(GameEventModel)
                        .where(
                            GameEventModel.player_id == event.player_id,
                            GameEventModel.session_id == event.session_id,
                            GameEventModel.event_type == "player_move",
                            GameEventModel.timestamp > cutoff,
                            GameEventModel.timestamp <= event.timestamp
                        )

                    )

                    recent_events = (await db.scalars(recent_events)).all()
                    
                    if len(recent_events) >= 20:
                        is_bot, deviation = self._check_bot_behavior(recent_events)
                        if is_bot:
                            severity = "high"
                        
                            await self._create_flag(
                                db,
                                player_id = event.player_id,
                                flag_type = "bot_behavior",
                                severity = severity,
                                context = {
                                    "session_id": event.session_id,
                                    "event_id": str(event.event_id),
                                    "std_dev": deviation
                                }
                            )
                            logger.warning("FLAG: Player %s is Botting!", event.player_id)
                        else:
                            logger.info("Player %s std deviation is %.2f", event.player_id, deviation)
                            

                if event.event_type == "score_update":
                    if event.metadata.score is None:
                        return None
                    
                    session_start = (
                        select(GameEventModel)
                        .where(
                            GameEventModel.player_id == event.player_id,
                            GameEventModel.session_id == event.session_id,
                            GameEventModel.event_type == "session_start"
                        )
                    )

                    session_start = await db.scalar(session_start)

                    if not session_start:
                        return

                    score_flagged, points_per_second = self._check_score_threshold(event, session_start)

                    if score_flagged:

                        severity = "low"

                        if 2000 <= points_per_second < 3000:
                            severity = "medium"
                        
                        elif 3000 <= points_per_second < 4000:
                            severity = "high"
                        
                        elif points_per_second >= 4000:
                            severity = "critical"
                        
                        await self._create_flag(
                            db,
                            player_id = event.player_id,
                            flag_type = "score_hack",
                            severity = severity,
                            context = {
                                "session_id": event.session_id,
                                "event_id": str(event.event_id),
                                "points_per_second": points_per_second
                            }
                        )
                        logger.warning("FLAG: Player %s suspected of an impossible score!", event.player_id)
                    else:
                        logger.info("Player %s score is  %.2f", event.player_id, points_per_second)

                        is_hack, z_score = await self._check_statistical_score(db, event)

                        if is_hack:

                            severity = "low"

                            if 3.5 <= z_score < 4:
                                severity = "medium"
                            
                            elif 4 <= z_score < 4.5:
                                severity = "high"
                            
                            elif z_score >= 4.5:
                                severity = "critical"
                            
                            await self._create_flag(
                                db,
                                player_id = event.player_id,
                                flag_type = "z_score_hack",
                                severity = severity,
                                context = {
                                    "session_id": event.session_id,
                                    "event_id": str(event.event_id),
                                    "z_score": z_score,
                                    "score": event.metadata.score
                                }
                            )
                            logger.warning("FLAG: Player %s suspected of an impossible score!", event.player_id)
                        else:
                            if z_score is not None:
                                logger.info("Player %s z_score is  %.2f", event.player_id, z_score)

                if event.event_type == "session_end":
                    
                    session_start = (
                        select(GameEventModel)
                        .where(
                            GameEventModel.player_id == event.player_id,
                            GameEventModel.session_id == event.session_id,
                            GameEventModel.event_type == "session_start"
                        )
                        )
                    session_start = await db.scalar(session_start)

                    if not session_start:
                            return
                    
                    is_hack, session_length = self._check_session_length(event, session_start)
                    
                    if is_hack:
                        
                        severity = "low"

                        if 7200 <= session_length < 21600:
                            severity = "medium"
                        
                        elif 21600 <= session_length < 43200:
                            severity = "high"
                        
                        elif session_length >= 43200:
                            severity = "critical"
                        
                        await self._create_flag(
                            db,
                            player_id = event.player_id,
                            flag_type = "session_hack",
                            severity = severity,
                            context = {
                                "session_id": event.session_id,
                                "event_id": str(event.event_id),
                                "session_length": session_length
                            }
                        )
                        logger.warning("FLAG: Player %s flagged as %s (%.0f s)", event.player_id, severity, session_length)

                    elif session_length is not None:
                        logger.info("Player %s session length %.2f", event.player_id, session_length)
                        

                
            except Exception:
                logger.exception("Error processing event %s", event.event_id)
                    
            logger.info("Analyzing event: %s", event.event_id)

    async def _create_flag(self, db: AsyncSession, player_id: str, flag_type: str, severity: str, context: dict) -> Playerflag:
        flag = Playerflag(
            player_id = player_id,
            flag_type = flag_type,
            severity = severity,
            timestamp = datetime.now(timezone.utc),
            status = "open",
            context = context
        )
        db.add(flag)
        await db.flush()
        await db.commit()
        return flag

    def _check_impossible_movement(self, event: GameEvent, previous_move: GameEventModel) -> tuple:

        if event.metadata.position is None:
            return False, None

        prev_pos = previous_move.event_data.get("position")
        if not prev_pos:
            return False, None

        prev_x = float(prev_pos["x"])
        prev_y = float(prev_pos["y"])

        curr_x = float(event.metadata.position["x"])
        curr_y = float(event.metadata.position["y"])

        distance = ((curr_x - prev_x)**2 + (curr_y - prev_y)**2)**0.5

        t_curr = event.timestamp.astimezone(timezone.utc)
                
        if previous_move.timestamp.tzinfo is None:
            t_prev = previous_move.timestamp.replace(tzinfo=timezone.utc)
        else:
            t_prev = previous_move.timestamp.astimezone(timezone.utc)

        time_delta = (t_curr - t_prev).total_seconds()

        logger.debug(
            "prev=%s, "
            "curr=%s, "
            "delta=%s",
            t_prev,
            t_curr,
            time_delta
        )

        speed = None
        if time_delta > 0:
            speed = distance / time_delta

            if speed > 1000:
                return True, speed
            
        return False, speed
    
    def _check_score_threshold(self, event: GameEvent, session_start: GameEventModel) -> tuple:

        t_curr = event.timestamp.astimezone(timezone.utc)

        if session_start.timestamp.tzinfo is None:
            start = session_start.timestamp.replace(tzinfo=timezone.utc)
        else:
            start = session_start.timestamp.astimezone(timezone.utc)

        duration = (t_curr - start).total_seconds()

        if duration <= 0:
            return False, None
        
        points_per_second = event.metadata.score / duration

        if points_per_second > 2000:
            return True, points_per_second
        
        return False, points_per_second
    
    def _check_bot_behavior(self, recent_events: Sequence) -> tuple:

        times = []

        for recent_event in recent_events:
            times.append(recent_event.timestamp)

        times.sort()

        intervals = []

        for i in range(1, len(times)):
            delta = (times[i] - times[i-1]).total_seconds()
            intervals.append(delta)
        
        if len(intervals) <= 1:
            return False, None
        
        stdev = statistics.stdev(intervals)

        if stdev <= 0.1:
            return True, stdev
        return False, stdev
    
    def _check_session_length(self, event: GameEvent, session_start: GameEventModel) -> tuple:

        t_curr = event.timestamp.astimezone(timezone.utc)

        if session_start.timestamp.tzinfo is None:
            start = session_start.timestamp.replace(tzinfo=timezone.utc)
        else:
            start = session_start.timestamp.astimezone(timezone.utc)

        duration = (t_curr - start).total_seconds()

        if duration <= 0:
            return False, None
        
        if duration >= 2700:
            return True, duration
        
        return False, duration
    
    async def _check_statistical_score(self, db: AsyncSession, event: GameEvent) -> tuple:
        from app.models.cohort_stats import CohortStats
        
        result = await db.execute(
            select(CohortStats).order_by(desc(CohortStats.computed_at)).limit(1)
        )
        stats = result.scalar_one_or_none()
        
        if stats is None:
            logger.warning("No cohort stats available, skipping Z-score check")
            return False, None
        
        if stats.stddev is None or float(stats.stddev) == 0: # type: ignore
            return False, None
        
        value = event.metadata.score
        z_score = (value - stats.mean) / stats.stddev

        if z_score > 3: #type: ignore
            return True, z_score
        
        return False, z_score
        
        
