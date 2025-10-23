import asyncio
import logging
from collections.abc import Callable, Coroutine
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from auth.client import get_service_token
from common.schemas import UpdateInventory
from core.config import get_settings
from core.db import session
from models.models import Inventory, PendingChange, SyncStatus
from observability import (
	inventory_count,
	pending_changes_gauge,
	push_response_seconds,
	sync_attempts_total,
	sync_conflicts_total,
	sync_duration_seconds,
	sync_failures_total,
	sync_success_total,
)

from .sync_service_db import (
	count,
	get_inventory,
	get_pending_changes,
	update_model,
)

logger = logging.getLogger(__name__)
settings = get_settings()


RETRY_DELAYS = [1, 2, 4, 8, 16, 32]  # Exponential backoff


async def with_retry(
	func_call: Callable[[], Coroutine[None, None, httpx.Response]],
	max_retries: int = len(RETRY_DELAYS),
) -> Any:
	"""Execute a provided coroutine factory with exponential backoff retry.

	`func_call` should be a zero-argument callable that returns an awaitable (e.g. a lambda).
	"""
	last_error = None
	for i in range(max_retries):
		try:
			sync_attempts_total.inc()
			return await func_call()
		except httpx.HTTPStatusError as e:
			if e.response.status_code == 409:
				sync_conflicts_total.inc()
				raise
			if 400 <= e.response.status_code < 500:
				sync_failures_total.inc()
				raise
			last_error = e
		except Exception as e:
			last_error = e

		if i < len(RETRY_DELAYS):
			delay = RETRY_DELAYS[i]
			logger.warning(f"Retry {i + 1}/{max_retries} after {delay}s: {last_error}")
			await asyncio.sleep(delay)

	sync_failures_total.inc()
	raise last_error


async def push_inventory_update(
	db: AsyncSession, change: PendingChange
) -> tuple[bool, str | None]:
	"""Push a single inventory update to central. Returns (success, error_message)."""
	try:
		token = await get_service_token()
		headers = {
			"Authorization": f"Bearer {token}",
			"Idempotency-Key": change.operation_id,
		}
		item = await get_inventory(id=change.inventory_id, db=db)
		update = UpdateInventory(
			sku=change.sku,
			delta=change.delta,
			version=change.central_version or item.version,
			operation_id=change.operation_id,
		)

		async with httpx.AsyncClient() as client:
			start_push = datetime.now(UTC)
			response: httpx.Response = await with_retry(
				lambda: client.post(
					f"{settings.central_url}/v1/inventory/{change.sku}/adjust",
					json=update.model_dump(),
					headers=headers,
				)
			)
			try:
				push_response_seconds.set(
					(datetime.now(UTC) - start_push).total_seconds()
				)
			except Exception:
				pass
			if response.status_code == 200:
				sync_success_total.inc()
				result = response.json()
				await update_model(
					model=Inventory,
					id=change.inventory_id,
					db=db,
					update_values={
						"version": result["version"],
						"last_synced_at": datetime.now(UTC),
					},
				)
				return True, None

			return False, f"Unexpected response: {response.status_code}"

	except httpx.HTTPStatusError as e:
		if e.response.status_code == 409:
			error_data = e.response.json()
			current = error_data.get("current_state", {})
			if current.get("version"):
				await update_model(
					model=PendingChange,
					id=change.id,
					db=db,
					update_values={"central_version": current["version"]},
				)
			sync_conflicts_total.inc()
			return False, "Version conflict with central"
		return False, f"HTTP error: {str(e)}"
	except Exception as e:
		sync_failures_total.inc()
		return False, f"Sync error: {str(e)}"


async def sync_pending_changes() -> None:
	"""Background task to sync pending inventory changes to central."""
	# Deprecated: use Celery tasks and `process_pending_once` for scheduling.
	logger.warning("sync_pending_changes loop is deprecated; use Celery tasks instead")


async def update_metrics(db: AsyncSession) -> None:
	"""Update inventory and pending changes metrics."""
	try:
		inventory_count.set(await count(db=db, model=Inventory))
		pending_changes_gauge.set(await count(db=db, model=PendingChange))
	except Exception:
		logger.exception("Failed to update metrics")

async def process_change(db: AsyncSession, change: PendingChange) -> bool:
	"""Process a single pending change. Returns True if processed successfully."""
	logger.info(f"Processing change {change.operation_id}")
	try:
		# Mark as in progress
		await update_model(
			model=PendingChange,
			id=change.id,
			db=db,
			update_values={
				"status": SyncStatus.IN_PROGRESS,
				"updated_at": datetime.now(UTC),
			},
		)

		success, error = await push_inventory_update(db, change)

		# Update final status
		await update_model(
			model=PendingChange,
			id=change.id,
			db=db,
			update_values={
				"status": SyncStatus.COMPLETED if success else SyncStatus.FAILED,
				"error": error,
				"updated_at": datetime.now(UTC),
			},
		)

		return True

	except Exception:
		logger.exception(f"Error processing change {change.operation_id}")
		await update_model(
			model=PendingChange,
			id=change.id,
			db=db,
			update_values={
				"status": SyncStatus.FAILED,
				"error": "internal error",
				"updated_at": datetime.now(UTC),
			},
		)
		return False

async def process_pending_once() -> int:
	"""Process a batch of pending changes once. Returns number processed."""
	processed = 0
	async with session() as db:
		try:
			# Get pending changes and update metrics
			changes = await get_pending_changes(db=db, status=SyncStatus.PENDING)
			await update_metrics(db)

			if not changes:
				return 0

			start = datetime.now(UTC)

			# Process changes concurrently in small batches
			batch_size = 5  # Adjust based on your needs
			for i in range(0, len(changes), batch_size):
				batch = changes[i:i + batch_size]
				results = await asyncio.gather(
					*[process_change(db, change) for change in batch],
					return_exceptions=False
				)
				processed += sum(1 for r in results if r)

		except Exception:
			logger.exception("Error in single-run sync")
		finally:
			# Record duration (best-effort)
			try:
				elapsed = (datetime.now(UTC) - start).total_seconds()
				sync_duration_seconds.set(float(elapsed))
			except Exception:
				logger.exception("Failed to record sync duration")

	return processed
