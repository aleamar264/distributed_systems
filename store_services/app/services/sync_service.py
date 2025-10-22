import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from auth.client import get_service_token
from common.schemas import UpdateInventory
from core.config import _env
from core.db import session
from models import Inventory, PendingChange, SyncStatus
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

logger = logging.getLogger(__name__)

RETRY_DELAYS = [1, 2, 4, 8, 16, 32]  # Exponential backoff


async def with_retry(
    func_call, max_retries: int = len(RETRY_DELAYS), initial_delay: float = 1.0
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
                # Conflict - caller should handle
                sync_conflicts_total.inc()
                raise
            if 400 <= e.response.status_code < 500:
                # Don't retry client errors
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

        # Get current inventory state
        inventory = await db.execute(
            select(Inventory).where(Inventory.id == change.inventory_id)
        )
        item = inventory.scalar_one()

        update = UpdateInventory(
            sku=change.sku,
            delta=change.delta,
            version=change.central_version or item.version,
            operation_id=change.operation_id,
        )

        async with httpx.AsyncClient() as client:
            # Measure push response time
            start_push = datetime.now(UTC)
            response = await with_retry(lambda: client.post(
                f"{_env.central_url}/v1/inventory/{change.sku}/adjust",
                json=update.model_dump(),
                headers=headers,
            ))
            try:
                push_response_seconds.set((datetime.now(UTC) - start_push).total_seconds())
            except Exception:
                pass
            
            if response.status_code == 200:
                # Update succeeded
                sync_success_total.inc()
                result = response.json()
                await db.execute(
                    update(Inventory)
                    .where(Inventory.id == change.inventory_id)
                    .values(
                        version=result["version"],
                        last_synced_at=datetime.now(UTC),
                    )
                )
                return True, None

            return False, f"Unexpected response: {response.status_code}"

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 409:
            # Version conflict - get current version from error response
            error_data = e.response.json()
            current = error_data.get("current_state", {})
            if current.get("version"):
                # Update our tracking of central's version
                await db.execute(
                    update(PendingChange)
                    .where(PendingChange.id == change.id)
                    .values(central_version=current["version"])
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


async def process_pending_once() -> int:
    """Process a batch of pending changes once. Returns number processed."""
    processed = 0
    async with session() as db:
        try:
            # Get pending changes
            result = await db.execute(
                select(PendingChange)
                .where(PendingChange.status == SyncStatus.PENDING)
                .order_by(PendingChange.created_at)
                .limit(100)
            )
            changes = result.scalars().all()

            # Update gauges with current counts
            try:
                inv_count = await db.execute(select(func.count()).select_from(Inventory))
                pending_count = await db.execute(select(func.count()).select_from(PendingChange))
                inventory_count.set(int(inv_count.scalar_one()))
                pending_changes_gauge.set(int(pending_count.scalar_one()))
            except Exception:
                pass

            if not changes:
                return 0

            start = datetime.now(UTC)
            for change in changes:
                logger.info(f"Processing change {change.operation_id}")
                try:
                    # Mark as in progress
                    await db.execute(
                        update(PendingChange)
                        .where(PendingChange.id == change.id)
                        .values(
                            status=SyncStatus.IN_PROGRESS,
                            updated_at=datetime.now(UTC),
                        )
                    )
                    await db.commit()

                    success, error = await push_inventory_update(db, change)

                    # Update status
                    await db.execute(
                        update(PendingChange)
                        .where(PendingChange.id == change.id)
                        .values(
                            status=SyncStatus.COMPLETED if success else SyncStatus.FAILED,
                            error=error,
                            updated_at=datetime.now(UTC),
                        )
                    )
                    await db.commit()

                    processed += 1

                except Exception:
                    logger.exception(f"Error processing change {change.operation_id}")
                    await db.execute(
                        update(PendingChange)
                        .where(PendingChange.id == change.id)
                        .values(
                            status=SyncStatus.FAILED,
                            error="internal error",
                            updated_at=datetime.now(UTC),
                        )
                    )
                    await db.commit()

        except Exception:
            logger.exception("Error in single-run sync")
        finally:
            # record duration (best-effort)
            try:
                elapsed = (datetime.now(UTC) - start).total_seconds()
                sync_duration_seconds.set(float(elapsed))
            except Exception:
                pass

    return processed
