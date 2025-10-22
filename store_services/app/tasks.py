import asyncio

from celery_app import celery_app
from services.sync_service import process_pending_once


@celery_app.task(name="store.process_pending_once")
def process_pending_once_task():
    """Celery task wrapper that runs the async processor once."""
    return asyncio.run(process_pending_once())
