from collections.abc import Sequence

from fastapi import HTTPException
from sqlalchemy import func, lambda_stmt, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.models import Inventory, PendingChange, SyncStatus


async def get_inventory(id: int, db: AsyncSession) -> Inventory:
	"""Get product of the inventory using the id
	Params:
	    id (int): Id of the product in the inventory
	    db (AsyncSession)
	Return:
	    Inventory
	Raises:
	    NoResultFound: If not result is found
	"""
	stmt = lambda_stmt(lambda: select(Inventory).where(Inventory.id == id))
	result = await db.execute(stmt)
	return result.scalar_one()


async def update_model(id: int, db: AsyncSession, update_values: dict, model) -> None:
	"""Update any model where the main filter is the id
	Params:
	    model (SqlAlchemyModel)
	    update_values (dict): Dictionary with the fields to update
	    db (AsyncSession)
	    id (int): Id of the model to update
	Return:
	    None
	"""
	stmt = update(model).where(model.id == id).values(**update_values)
	await db.execute(stmt)
	await db.commit()


async def get_pending_changes(db: AsyncSession, status: SyncStatus) -> Sequence[PendingChange]:
	_status = status.value
	stmt = (select(PendingChange)
		.where(PendingChange.status == _status)
		.order_by(PendingChange.created_at)
		.limit(100))

	result = await db.execute(stmt)
	return result.scalars().all()

async def get_pending_change_by_sku(db: AsyncSession, sku: str) -> str:
	stmt = lambda_stmt(
		lambda: select(PendingChange.operation_id)
		.where(PendingChange.sku == sku)
	)
	result = await db.execute(stmt)
	item = result.first()
	if not item:
		raise HTTPException(status_code=404, detail="No item for change for SKU {sku}")
	return item.operation_id

async def count(db:AsyncSession, model)->int:
	res = await db.execute(select(func.count()).select_from(model))
	return res.scalar_one()