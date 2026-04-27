from sqlalchemy import Column, Integer, Float, DateTime
from sqlalchemy.sql import func
from app.db.database import Base

class CohortStats(Base):
    __tablename__ = "cohort_stats"

    id = Column(Integer, primary_key=True)
    mean = Column(Float, nullable=False)
    stddev = Column(Float, nullable=False)
    computed_at = Column(DateTime(timezone=True), server_default=func.now())