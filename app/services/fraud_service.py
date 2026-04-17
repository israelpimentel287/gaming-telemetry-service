from sqlalchemy import desc, func
from app.models.event import GameEventModel
from app.models.player_flag import Playerflag
from app.schemas.event import GameEvent
from app.db.database import SessionLocal
from datetime import timezone, datetime, timedelta
import statistics
ANALYZED_EVENTS = {"player_move", "score_update", "session_end"}

class FraudDetectionService:

    def analyze_event(self, event: GameEvent)-> None:

        if event.event_type not in ANALYZED_EVENTS:
            return
        
        db = SessionLocal()
        
        try:
            if event.event_type == "player_move":
                if event.metadata.position is None:
                     return
                
                previous_move = (
                    db.query(GameEventModel)
                    .filter(
                        GameEventModel.player_id == event.player_id,
                        GameEventModel.session_id == event.session_id,
                        GameEventModel.event_type == "player_move",
                        GameEventModel.timestamp < event.timestamp
                    )
                    .order_by(desc(GameEventModel.timestamp))
                    .first()
                )

                if previous_move:
                    is_hack, speed = self._check_impossible_movement(event, previous_move)

                    if speed is not None and is_hack:

                        severity = "medium"
                        
                        if 1000 <= speed < 5000:
                            severity = "high"
                        elif speed >= 5000 :
                            severity = "critical"

                        self._create_flag(
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
                        print(f"FLAG: Player {event.player_id} suspected of speed hacking!")
                    elif speed is not None:
                        print(f"Player {event.player_id} moved at {speed:.2f} units/sec")

                cutoff = event.timestamp - timedelta(seconds=30)

                recent_events = (
                    db.query(GameEventModel)
                    .filter(
                        GameEventModel.player_id == event.player_id,
                        GameEventModel.session_id == event.session_id,
                        GameEventModel.event_type == "player_move",
                        GameEventModel.timestamp > cutoff
                    )
                    .all()

                )
                
                if len(recent_events) >= 20:
                    is_bot, deviation = self._check_bot_behavior(recent_events)
                    if is_bot:
                        severity = "high"
                    
                        self._create_flag(
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
                        print(f"FLAG: Player {event.player_id} is Botting!")
                    else:
                        print(f"Player {event.player_id} std deviation is {deviation:.2f}")
                        

            if event.event_type == "score_update":
                if event.metadata.score is None:
                    return None
                
                session_start = (
                    db.query(GameEventModel)
                    .filter(
                        GameEventModel.player_id == event.player_id,
                        GameEventModel.session_id == event.session_id,
                        GameEventModel.event_type == "session_start"
                    )
                    .first()
                )

                if not session_start:
                    return

                is_hack, points_per_second = self._check_score_threshold(event, session_start)

                if is_hack:

                    severity = "low"

                    if 2000 <= points_per_second < 3000:
                        severity = "medium"
                    
                    elif 3000 <= points_per_second < 4000:
                        severity = "high"
                    
                    elif points_per_second >= 4000:
                        severity = "critical"
                    
                    self._create_flag(
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
                    print(f"FLAG: Player {event.player_id} suspected of an impossible score!")
                else:
                    print(f"Player {event.player_id} score is  {points_per_second:.2f}")

                is_hack, z_score = self._check_statistical_score(db, event)

                if is_hack:

                    severity = "low"

                    if 3.5 <= z_score < 4:
                        severity = "medium"
                    
                    elif 4 <= z_score < 4.5:
                        severity = "high"
                    
                    elif z_score >= 4.5:
                        severity = "critical"
                    
                    self._create_flag(
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
                    print(f"FLAG: Player {event.player_id} suspected of an impossible score!")
                else:
                    if z_score is not None:
                        print(f"Player {event.player_id} z_score is  {z_score:.2f}")

            if event.event_type == "session_end":
                
                session_start = (
                    db.query(GameEventModel)
                    .filter(
                        GameEventModel.player_id == event.player_id,
                        GameEventModel.session_id == event.session_id,
                        GameEventModel.event_type == "session_start"
                    )
                    .first()
                    )
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
                    
                    self._create_flag(
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
                    print(f"FLAG: Player {event.player_id} flagged as {severity} ({session_length:.0f}s)")

                elif session_length is not None:
                    print(f"Player {event.player_id} session length {session_length:.2f}")
                    

                
        except (KeyError, TypeError, ValueError):
            print("Error processing event")
            
        finally:
            db.close()
                
        print(f"Analyzing event: {event.event_id}")


    def _create_flag(self, db, player_id: str, flag_type: str, severity: str, context: dict) -> Playerflag:
        flag = Playerflag(
            player_id = player_id,
            flag_type = flag_type,
            severity = severity,
            timestamp = datetime.now(timezone.utc),
            status = "open",
            context = context
        )
        db.add(flag)
        db.flush()
        db.commit()
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

        print(
            f"DEBUG -> "
            f"prev={t_prev}, "
            f"curr={t_curr}, "
            f"delta={time_delta}"
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
    
    def _check_bot_behavior(self, recent_events: list) -> tuple:

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
    
    def _check_statistical_score(self, db, event: GameEvent) -> tuple:

        flagged_players = db.query(Playerflag.player_id).distinct()
        
        result = db.query(
            func.avg(GameEventModel.event_data["score"].as_float()),
            func.stddev(GameEventModel.event_data["score"].as_float()),
            func.count(GameEventModel.event_id)
        ).filter(
            GameEventModel.event_type == "score_update",
            GameEventModel.player_id.notin_(flagged_players)
        ).first()
           
        mean, std_dev, count = result

        if count < 10:
            return False,None
        
        if std_dev is None or std_dev == 0:
            return False, None
        
        value = event.metadata.score
        z_score = (value - mean) / std_dev

        if z_score > 3:
            return True, z_score
        
        return False, z_score
        
        
