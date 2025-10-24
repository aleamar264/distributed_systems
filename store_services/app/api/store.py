import logging
from datetime import UTC, datetime
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from common.schemas import GenericResponse, InventoryResponse, UpdateInventory
from core.db import get_db
from models.models import Inventory, PendingChange, SyncStatus
from observability import local_updates_total
from services.api_services import get_inventory_by_sku, get_pending_change
from services.sync_service_db import get_inventory as getInventory
from services.sync_service_db import get_pending_change_by_sku, update_model

try:
	from celery_tools.celery_tasks.tasks import process_pending_once_task
except Exception:
	process_pending_once_task = None


router = APIRouter(prefix="/v1/local", tags=["store"])
logger = logging.getLogger("store_service")


@router.get("/inventory/{sku}", response_model=InventoryResponse)
async def get_inventory(
	sku: str, db: Annotated[AsyncSession, Depends(get_db)], request: Request
) -> InventoryResponse:
	"""Get local inventory state."""

	try:
		item = await get_inventory_by_sku(
			sku=sku, db=db, request=request, logger=logger
		)
		logger.info(
			f"Retrieved inventory for SKU: {sku}",
			extra={
				"request_id": request.state.request_id,
				"sku": sku,
				"quantity": item.quantity,
				"version": item.version,
			},
		)
		return InventoryResponse.model_validate(item)
	except HTTPException:
		raise
	except Exception as e:
		logger.error(
			f"Error retrieving inventory: {str(e)}",
			extra={"request_id": request.state.request_id, "sku": sku, "error": str(e)},
			exc_info=True,
		)
		raise HTTPException(
			status_code=500, detail="Internal server error while retrieving inventory"
		) from e


@router.post("/inventory/{sku}/update", response_model=InventoryResponse)
async def update_inventory(
	sku: str,
	payload: UpdateInventory,
	db: Annotated[AsyncSession, Depends(get_db)],
	request: Request,
) -> InventoryResponse:
	"""Update local inventory and queue change for central sync."""
	# Get current inventory
	item = await get_inventory_by_sku(
		logger=logger, request=request, db=db, wait_update=True, sku=sku
	)
	# Apply local update
	new_qty = item.quantity + payload.delta
	if new_qty < 0:
		raise HTTPException(
			status_code=400,
			detail=f"Insufficient quantity. Available: {item.quantity}, requested: {abs(payload.delta)}",
		)

	# Update local inventory
	new_version = item.version + 1
	await update_model(
		model=Inventory,
		update_values={
			"quantity": new_qty,
			"version": new_version,
			"updated_at": datetime.now(UTC),
		},
		db=db,
		id=item.id,
	)

	# Queue change for sync
	change = PendingChange(
		operation_id=payload.operation_id or str(uuid4()),
		inventory_id=item.id,
		sku=item.sku,
		delta=payload.delta,
		local_version=item.version + 1,
		central_version=payload.version,
		status=SyncStatus.PENDING.value,
	)
	db.add(change)
	await db.commit()
	# Instrument local update
	try:
		local_updates_total.inc()
	except Exception:
		pass

	# Return updated inventory
	result = await getInventory(id=item.id, db=db)
	return InventoryResponse.model_validate(result)


@router.get("/inventory/{sku}/operation_id")
async def get_operation_id(sku: str,  db: Annotated[AsyncSession, Depends(get_db)]):
	operation_id = await get_pending_change_by_sku(db=db, sku=sku)
	return JSONResponse({"operation_id": operation_id})


@router.get("/sync/status/{operation_id}", response_model=GenericResponse)
async def get_sync_status(
	operation_id: str, db: Annotated[AsyncSession, Depends(get_db)]
) -> GenericResponse:
	"""Check sync status of a change by operation ID."""
	change = await get_pending_change(db=db, operation_id=operation_id)
	return GenericResponse(
		ok=change.status == SyncStatus.COMPLETED.value,
		message=f"Sync status: {change.status}"
		+ (f" - {change.error}" if change.error else ""),
	)


@router.post("/sync/trigger")
async def trigger_sync(background: BackgroundTasks):
	"""Trigger a sync run: schedule via Celery if available, otherwise run background async task."""
	if process_pending_once_task:
		# Enqueue Celery task
		process_pending_once_task.delay()
		return GenericResponse(ok=True, message="Sync enqueued via Celery")

	# Fallback: run in background (best-effort)
	from services.sync_service import process_pending_once

	async def _run_once():
		await process_pending_once()

	background.add_task(_run_once)
	return GenericResponse(ok=True, message="Sync scheduled in background")
