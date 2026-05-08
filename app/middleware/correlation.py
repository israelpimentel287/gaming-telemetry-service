import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from app.core.context import correlation_id

class CorrelationIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        correlation_id.set(request_id)
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = request_id
        return response