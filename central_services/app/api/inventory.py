from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from common.schemas import UpdateInventory, UpdateInventoryResponse
from core.dependencies import get_db
from service.inventory import get_data_from_sku
from service.inventory import update_inventory as update_inventory_services

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.post("/update", response_model=UpdateInventoryResponse)
async def update_inventory(
	payload: UpdateInventory, db: AsyncSession = Depends(get_db)
):
	async with db.begin():
		item = await get_data_from_sku(payload.sku, db)
		if UpdateInventory.version <= item.version:
			raise HTTPException(409, f"Stale update. Current version {item.version}")

		new_quantity = item.quantity + payload.delta
		update_values = {
			"quantity": new_quantity,
			"version": item.version,
			"updated_at": datetime.now(UTC),
		}
		await update_inventory_services(
			db=db, update_values=update_values, sku=payload.sku
		)
	return UpdateInventoryResponse(
		**{"sku": payload.sku, "quantity": new_quantity, "version": payload.version}
	)
