import asyncio
import logging

from celery import shared_task

from services.sync_service import process_pending_once

logger = logging.getLogger(__name__)
@shared_task(
	bind=True,
	autoretry_for=(Exception,),
	retry_backoff=True,
	retry_kwargs={"max_retries": 5},
	acks_late=True,
	name="Store:process_pending_once_task",
)
def process_pending_once_task(self):
	"""Celery task wrapper that runs the async processor once."""
	logger.info("Executing task in background")
	return asyncio.run(process_pending_once())
