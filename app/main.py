from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.api.v1.endpoints.events import router
from app.api.v1.endpoints.metrics import router as metrics_router
from app.scheduler import scheduler, compute_cohort_stats

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

app.include_router(router, prefix="/v1")
app.include_router(metrics_router, prefix="/v1")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}