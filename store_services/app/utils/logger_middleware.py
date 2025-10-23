import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from utils.log_config import setup_logging

logger = setup_logging("store_service")

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        logger.info(f"Started request {request.method} {request.url}", extra={
            "request_id": request_id,
            "method": request.method,
            "path": str(request.url),
        })
        try:
            response = await call_next(request)
            logger.info(f"Completed request {request.method} {request.url}", extra={
                "request_id": request_id,
                "status_code": response.status_code,
            })
            return response
        except Exception as e:
            logger.error(f"Request failed: {str(e)}", extra={
                "request_id": request_id,
                "error": str(e),
            }, exc_info=True)
            raise
