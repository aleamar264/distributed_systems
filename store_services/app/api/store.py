import logging
from datetime import UTC, datetime
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from common.schemas import GenericResponse, InventoryResponse, UpdateInventory
from core.db import get_db
from models import Inventory, PendingChange, SyncStatus
from observability import local_updates_total
from fastapi import BackgroundTasks

try:
    from tasks import process_pending_once_task
except Exception:
    process_pending_once_task = None


router = APIRouter(prefix="/v1/local", tags=["store"])


@router.get("/inventory/{sku}", response_model=InventoryResponse)
async def get_inventory(
    sku: str, 
    db: Annotated[AsyncSession, Depends(get_db)],
    request: Request
) -> InventoryResponse:
    """Get local inventory state."""
    logger = logging.getLogger("store_service")
    try:
        result = await db.execute(select(Inventory).where(Inventory.sku == sku))
        item = result.scalar_one_or_none()
        if not item:
            logger.warning(f"SKU not found: {sku}", extra={
                "request_id": request.state.request_id,
                "sku": sku
            })
            raise HTTPException(status_code=404, detail="SKU not found")
        
        logger.info(f"Retrieved inventory for SKU: {sku}", extra={
            "request_id": request.state.request_id,
            "sku": sku,
            "quantity": item.quantity,
            "version": item.version
        })
        return InventoryResponse.model_validate(item)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving inventory: {str(e)}", extra={
            "request_id": request.state.request_id,
            "sku": sku,
            "error": str(e)
        }, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Internal server error while retrieving inventory"
        )


@router.post("/inventory/{sku}/update", response_model=InventoryResponse)
async def update_inventory(
    sku: str,
    payload: UpdateInventory,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> InventoryResponse:
    """Update local inventory and queue change for central sync."""
    # Get current inventory
    result = await db.execute(
        select(Inventory).where(Inventory.sku == sku).with_for_update()
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="SKU not found")

    # Apply local update
    new_qty = item.quantity + payload.delta
    if new_qty < 0:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient quantity. Available: {item.quantity}, requested: {abs(payload.delta)}",
        )

    # Update local inventory
    await db.execute(
        update(Inventory)
        .where(Inventory.id == item.id)
        .values(
            quantity=new_qty,
            version=item.version + 1,
            updated_at=datetime.now(UTC),
        )
    )

    # Queue change for sync
    change = PendingChange(
        operation_id=payload.operation_id or str(uuid4()),
        inventory_id=item.id,
        sku=item.sku,
        delta=payload.delta,
        local_version=item.version + 1,
        central_version=payload.version,  # Track central's version if known
        status=SyncStatus.PENDING,
    )
    db.add(change)
    await db.commit()
    # Instrument local update
    try:
        local_updates_total.inc()
    except Exception:
        pass

    # Return updated inventory
    result = await db.execute(select(Inventory).where(Inventory.id == item.id))
    return InventoryResponse.model_validate(result.scalar_one())


@router.get("/sync/status/{operation_id}", response_model=GenericResponse)
async def get_sync_status(
    operation_id: str, db: Annotated[AsyncSession, Depends(get_db)]
) -> GenericResponse:
    """Check sync status of a change by operation ID."""
    result = await db.execute(
        select(PendingChange).where(PendingChange.operation_id == operation_id)
    )
    change = result.scalar_one_or_none()
    if not change:
        raise HTTPException(status_code=404, detail="Operation not found")
    
    return GenericResponse(
        ok=change.status == SyncStatus.COMPLETED,
        message=f"Sync status: {change.status}" + (f" - {change.error}" if change.error else ""),
    )


@router.post('/sync/trigger')
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
