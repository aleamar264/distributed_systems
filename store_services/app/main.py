from datetime import UTC, datetime

from fastapi import FastAPI, Response
from fastapi.security import HTTPBearer
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from api.store import router as store_routes

from celery_tools.config.celery_utils import create_celery
# from celery_app import celery_app
from common.schemas import GenericResponse
from core.db import session
from models.models import Inventory, PendingChange
from observability import REGISTRY, inventory_count, pending_changes_gauge
from services.sync_service_db import count
from utils.logger_middleware import RequestLoggingMiddleware, logger

app = FastAPI()
app.celery_app = create_celery()
# app.celery_app = celery_app
bearer = HTTPBearer()
app.include_router(store_routes)

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


celery = app.celery_app  # type: ignore