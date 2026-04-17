from sqlalchemy import Column, DateTime, String, Integer
from sqlalchemy.dialects.postgresql import JSONB
from app.db.database import Base

class Playerflag(Base):
    __tablename__ = "player_flag"

    flag_id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(String, index=True)
    flag_type = Column(String)
    severity = Column(String)
    timestamp = Column(DateTime(timezone=True), index=True)
    context = Column(JSONB)
    status = Column(String)