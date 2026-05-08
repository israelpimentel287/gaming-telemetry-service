import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from app.core.logging import get_logger

logger = get_logger("http")

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        logger.info("Request started", extra={
            "method": request.method,
            "path": request.url.path
        })

        start = time.time()
        response = await call_next(request)
        duration_ms = round((time.time() - start) * 1000, 2)

        logger.info("Request finished", extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "durations_ms": duration_ms
        })

        return response