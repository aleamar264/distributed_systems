import logging
import uuid
from datetime import datetime, UTC

from fastapi import Depends, FastAPI, Request, Response
from fastapi.security import HTTPBearer
from sqlalchemy import select, func
from starlette.middleware.base import BaseHTTPMiddleware

from common.schemas import GenericResponse
from .api.store import router as store_routes
from .core.db import session
from .models import Inventory, PendingChange
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from .observability import REGISTRY, inventory_count, pending_changes_gauge
from utils.log_config import setup_logging

# Setup structured logging
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

app = FastAPI()
bearer = HTTPBearer()
app.include_router(store_routes, dependencies=[Depends(bearer)])

# Add request logging middleware
app.add_middleware(RequestLoggingMiddleware)

# Track process start for simple uptime metric
START_TIME = datetime.now(UTC)
logger.info("Store service started", extra={"start_time": START_TIME.isoformat()})


@app.get("/health", tags=["health"], response_model=GenericResponse)
def health_check() -> GenericResponse:
    return GenericResponse(ok=True, message="store healthy")


@app.get("/metrics", tags=["observability"])
async def metrics():
    async with session() as db:
        inv_res = await db.execute(select(func.count()).select_from(Inventory))
        inv_count = inv_res.scalar_one()
        pending_res = await db.execute(select(func.count()).select_from(PendingChange))
        pending_count = pending_res.scalar_one()

    # Update gauges
    inventory_count.set(int(inv_count))
    pending_changes_gauge.set(int(pending_count))

    # Return Prometheus text format
    output = generate_latest(REGISTRY)
    return Response(content=output, media_type=CONTENT_TYPE_LATEST)
