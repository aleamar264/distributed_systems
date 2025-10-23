from datetime import UTC, datetime

from fastapi import Depends, FastAPI, Response
from fastapi.security import HTTPBearer
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import func, select

from common.schemas import GenericResponse
from models.models import Inventory, PendingChange
from utils.logger_middleware import RequestLoggingMiddleware, logger

from .api.store import router as store_routes
from .core.db import session
from .observability import REGISTRY, inventory_count, pending_changes_gauge
from services.sync_service_db import count

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
        inv_count = await count(db=db, model=Inventory)
        pending_count = await count(db=db, model= PendingChange)

    # Update gauges
    inventory_count.set(inv_count)
    pending_changes_gauge.set(pending_count)

    # Return Prometheus text format
    output = generate_latest(REGISTRY)
    return Response(content=output, media_type=CONTENT_TYPE_LATEST)
