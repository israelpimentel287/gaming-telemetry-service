from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.events import router
from app.api.v1.endpoints.metrics import router as metrics_router
from app.core.exceptions import (
    AppException,
    app_exception_handler,
    unhandled_exception_handler,
)
from app.core.logging import setup_logging
from app.dependencies import get_db
from app.middleware.correlation import CorrelationIDMiddleware
from app.middleware.logging import LoggingMiddleware
from app.scheduler import compute_cohort_stats, scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.add_job(compute_cohort_stats, "interval", minutes=5)
    scheduler.start()
    await compute_cohort_stats()
    yield
    scheduler.shutdown()

app = FastAPI(
    title="Gaming Telemetry Service",
    description ="Event ingestion and fraud detection",
    version="1.0.0",
    lifespan=lifespan
)

app.add_exception_handler(AppException, app_exception_handler) # type: ignore
app.add_exception_handler(Exception, unhandled_exception_handler)

setup_logging()
app.add_middleware(LoggingMiddleware)
app.add_middleware(CorrelationIDMiddleware)


app.include_router(router, prefix="/v1")
app.include_router(metrics_router, prefix="/v1")

@app.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "healthy"}
    except Exception:
        return JSONResponse(status_code=503, content={"status": "unhealthy"})
