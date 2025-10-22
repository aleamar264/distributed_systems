from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from auth.utils import VerifiedService, get_db, verify_service_jwt
from common.schemas import (
	BulkSyncRequest,
	ConflictError,
	InventoryResponse,
	UpdateInventory,
)
from models.models import IdempotencyKey, Inventory
from observability import (
    inventory_updates_total,
    inventory_update_conflicts_total,
    inventory_update_failures_total,
    bulk_sync_total,
)

router = APIRouter(prefix="/v1", tags=["central"])


@router.get("/inventory/{sku}", response_model=InventoryResponse)
async def get_inventory(
	sku: str,
	db: Annotated[AsyncSession, Depends(get_db)],
	service: Annotated[VerifiedService, Depends(verify_service_jwt)],
) -> InventoryResponse:
	"""Get current inventory state for a SKU."""
	result = await db.execute(select(Inventory).where(Inventory.sku == sku))
	item = result.scalar_one_or_none()
	if not item:
		raise HTTPException(status_code=404, detail="SKU not found")
	return item


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
		# Check idempotency
		idem_key = await db.execute(
			select(IdempotencyKey).where(
				IdempotencyKey.key == idempotency_key,
				IdempotencyKey.service_name == service["service_name"],
				IdempotencyKey.expires_at > datetime.now(UTC),
			)
		)
		existing = idem_key.scalar_one_or_none()
		if existing:
			# Return cached response for idempotent retry
			result = await db.execute(select(Inventory).where(Inventory.sku == sku))
			return result.scalar_one()

		# Get current item state
		result = await db.execute(
			select(Inventory).where(Inventory.sku == sku).with_for_update()
		)
		item = result.scalar_one_or_none()
		if not item:
			raise HTTPException(status_code=404, detail="SKU not found")

		if item.version != payload.version:
			# Version mismatch - return 409 with current state
			inventory_update_conflicts_total.inc()
			raise HTTPException(
				status_code=409,
				detail=ConflictError(
					message="Optimistic lock failed - item was updated",
					current_state=InventoryResponse.model_validate(item),
				).model_dump(),
			)

		# Apply update with version check
		new_qty = item.quantity + payload.delta
		if new_qty < 0:
			raise HTTPException(
				status_code=400,
				detail=f"Insufficient quantity. Available: {item.quantity}, requested: {abs(payload.delta)}",
			)

		result = await db.execute(
			update(Inventory)
			.where(Inventory.sku == sku, Inventory.version == payload.version)
			.values(
				quantity=new_qty,
				version=Inventory.version + 1,
				updated_at=datetime.now(UTC),
			)
			.returning(Inventory)
		)
		updated = result.scalar_one()

		# Store idempotency key (upsert-like behavior)
		await db.execute(
			update(IdempotencyKey)
			.where(IdempotencyKey.key == idempotency_key)
			.values(
				service_name=service["service_name"],
				request_hash=str(payload.model_dump()),
				response_body=str(updated.model_dump()),
				expires_at=datetime.now(UTC) + timedelta(hours=24),
			)
		)
		await db.commit()

		inventory_updates_total.inc()
		return updated
	except HTTPException:
		# Let HTTP exceptions through (they're intentional)
		raise
	except Exception:
		# Count unexpected failures
		inventory_update_failures_total.inc()
		raise


@router.post("/inventory/bulk-sync", response_model=list[InventoryResponse])
async def bulk_sync(
	payload: BulkSyncRequest,
	db: Annotated[AsyncSession, Depends(get_db)],
	service: Annotated[VerifiedService, Depends(verify_service_jwt)],
) -> list[InventoryResponse]:
	"""Process a batch of inventory updates for store sync."""
	results = []
	try:
		for item in payload.items:
			try:
				result = await adjust_inventory(
					item.sku,
					item,
					db,
					service,
					idempotency_key=f"bulk-{item.operation_id}",
				)
				results.append(result)
			except HTTPException as e:
				if e.status_code == 409:
					# For bulk sync, if there's a conflict, just get latest
					result = await db.execute(
						select(Inventory).where(Inventory.sku == item.sku)
					)
					results.append(result.scalar_one())
				else:
					raise
	except Exception:
		inventory_update_failures_total.inc()
		raise
	finally:
		bulk_sync_total.inc()

	return results
