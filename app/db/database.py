from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.config import settings

engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size = 66,
    max_overflow = 33,
    pool_timeout = 5
)

SessionLocal = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()