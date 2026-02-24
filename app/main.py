from fastapi import FastAPI
from app.api.v1.endpoints.events import router

app = FastAPI(
    title="Gaming Telemetry Service",
    description ="Event ingestion and fraud detection",
    version="1.0.0"
)

app.include_router(router, prefix="/v1")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}