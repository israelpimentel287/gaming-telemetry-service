from fastapi import FastAPI
from app.api.v1.endpoints.events import router
from app.db.database import Base, engine
from app.models.event import GameEventModel # noqa: F401

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Gaming Telemetry Service",
    description ="Event ingestion and fraud detection",
    version="1.0.0"
)

app.include_router(router, prefix="/v1")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}