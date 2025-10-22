import uuid
from datetime import UTC, datetime

from fastapi import FastAPI, Request, Response
from sqlalchemy import func, select
from starlette.middleware.base import BaseHTTPMiddleware

from utils.log_config import setup_logging

# Setup structured logging
logger = setup_logging("central_service")


from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from api.central import router as central_routes
from auth.routes import router as auth_route
from common.schemas import GenericResponse
from core.db import session
from logging_config import configure_logging
from models.models import IdempotencyKey, Inventory
from observability import REGISTRY, idempotency_keys_gauge, inventory_count_gauge

# Configure structured logging
configure_logging()


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

app = FastAPI()
app.include_router(central_routes)
app.include_router(auth_route)

# Add request logging middleware
app.add_middleware(RequestLoggingMiddleware)

# Track process start for simple uptime metric
START_TIME = datetime.now(UTC)
logger.info("Central service started", extra={"start_time": START_TIME.isoformat()})

@app.get("/health", tags=["health"], response_model=GenericResponse)
def health_check() -> GenericResponse:
    return GenericResponse(ok=True, message="central healthy")


@app.get("/metrics", tags=["observability"])
async def metrics():
    """Return simple observability metrics: uptime and DB counts."""
    async with session() as db:
        inv_res = await db.execute(select(func.count()).select_from(Inventory))
        inv_count = inv_res.scalar_one()
        idem_res = await db.execute(select(func.count()).select_from(IdempotencyKey))
        idem_count = idem_res.scalar_one()

    uptime = (datetime.now(UTC) - START_TIME).total_seconds()
    # Update gauges
    inventory_count_gauge.set(int(inv_count))
    idempotency_keys_gauge.set(int(idem_count))

    # Return Prometheus text format
    output = generate_latest(REGISTRY)
    return Response(content=output, media_type=CONTENT_TYPE_LATEST)
