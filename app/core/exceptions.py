from fastapi import Request
from fastapi.responses import JSONResponse
from app.core.logging import get_logger

logger = get_logger("exceptions")

class AppException(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail

async def app_exception_handler(request: Request, exc: AppException):
    logger.warning("Expected error", extra={
        "status_code": exc.status_code,
        "detail": exc.detail
    })
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception", extra={
        "error": str(exc),
        "path": request.url.path
    })
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})