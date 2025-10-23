import asyncio
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth.utils import VerifiedService, get_db, verify_service_jwt
from common.schemas import (
	BulkSyncRequest,
	InventoryResponse,
	UpdateInventory,
)
from models.models import Inventory
from observability import (
	bulk_sync_total,
	inventory_update_failures_total,
	inventory_updates_total,
)
from service.inventory import (
	adjust_inventory_services,
	get_idempotency,
	get_item_from_sku,
)

logger = logging.getLogger("central_service")

router = APIRouter(prefix="/v1", tags=["central"])


@router.get("/inventory/{sku}", response_model=InventoryResponse)
async def get_inventory(
	sku: str,
	db: Annotated[AsyncSession, Depends(get_db)],
	service: Annotated[VerifiedService, Depends(verify_service_jwt)],
) -> InventoryResponse:
	"""Get current inventory state for a SKU."""
	return await get_item_from_sku(db=db, sku=sku)


@router.post("/inventory/{sku}/adjust", response_model=InventoryResponse)
async def adjust_inventory(
	sku: str,
	payload: UpdateInventory,
	db: Annotated[AsyncSession, Depends(get_db)],
	service: Annotated[VerifiedService, Depends(verify_service_jwt)],
	idempotency_key: str = Header(..., alias="Idempotency-Key"),
) -> InventoryResponse:
	"""Adjust inventory quantity for a SKU with optimistic locking."""
	try:
		existing = get_idempotency(
			db=db, idempotency_key=idempotency_key, service_name=service["service_name"]
		)
		if existing:
			return await get_item_from_sku(db=db, sku=sku)

		updated = await adjust_inventory_services(
			db=db,
			payload=payload,
			sku=sku,
			service_name=service["service_name"],
			idempotency_key=idempotency_key,
		)
		inventory_updates_total.inc()
		return updated
	except HTTPException:
		raise
	except Exception:
		inventory_update_failures_total.inc()
		raise


@router.post("/inventory/bulk-sync", response_model=list[InventoryResponse])
async def bulk_sync(
	payload: BulkSyncRequest,
	db: Annotated[AsyncSession, Depends(get_db)],
	service: Annotated[VerifiedService, Depends(verify_service_jwt)],
) -> list[InventoryResponse]:
	"""Process a batch of inventory updates for store sync."""
	results: list[InventoryResponse] = []
	semaphore = asyncio.Semaphore(10)

	async def _process_item(item: UpdateInventory) -> InventoryResponse:
		"""Process a single item from the bulk request.

		Uses the existing `adjust_inventory` endpoint logic via internal call to
		keep behaviour consistent (idempotency + optimistic locking).
		If a conflict (409) occurs, return the current state from DB.
		"""
		async with semaphore:
			try:
				resp = await adjust_inventory(
					item.sku,
					item,
					db,
					service,
					idempotency_key=f"bulk-{item.operation_id}",
				)
				return resp
			except HTTPException as e:
				if e.status_code == 409:
					# Conflict: return current state
					logger.debug("Conflict during bulk-sync for SKU %s", item.sku)
					result = await db.execute(select(Inventory).where(Inventory.sku == item.sku))
					item = result.scalar_one()
					return InventoryResponse.model_validate(item)
				raise

	# Launch tasks and gather results preserving order
	try:
		tasks = [asyncio.create_task(_process_item(it)) for it in payload.items]
		gathered = await asyncio.gather(*tasks)
		results.extend(gathered)
	except Exception as err:
		inventory_update_failures_total.inc()
		logger.exception("bulk_sync failed")
		raise
	finally:
		bulk_sync_total.inc()

	try:
		for _r in results:
			inventory_updates_total.inc()
	except Exception:
		pass

	return results
