from sqlalchemy import lambda_stmt, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from common.schemas import GetDataFromSku
from models.models import Inventory


async def get_data_from_sku(sku: str, db: AsyncSession) -> GetDataFromSku:
	stmt = lambda_stmt(
		select(Inventory.id, Inventory.quantity, Inventory.version).where(
			Inventory.sku == sku
		)
	)
	result = await db.execute(stmt)
	item = result.first()
	return GetDataFromSku.model_validate(item)


async def update_inventory(db: AsyncSession, sku: str, update_values: dict) -> None:
	stmt = update(Inventory).where(Inventory.sku == sku).values(**update_values)
	await db.execute(stmt)
