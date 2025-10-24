from ast import Assert
from logging import Logger

from fastapi import HTTPException, Request
from sqlalchemy import lambda_stmt, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.models import Inventory, PendingChange


async def get_inventory_by_sku(
	sku: str,
	db: AsyncSession,
	logger: Logger,
	request: Request,
	wait_update: bool = False,
) -> Inventory:
	"""Get a single item by SKU with logger
	Params:
	    sku (str): Unique Identifier for the inventory
	    db (AsyncSession)
	    logger (Logger)
	    request (Request)
	Return:
	    Iventory
	Raises:
	    HTTPException"""
	stmt = lambda_stmt(lambda: select(Inventory).where(Inventory.sku == sku))
	if wait_update:
		stmt += lambda s: s.with_for_update()
	result = await db.execute(stmt)
	item = result.scalar_one_or_none()
	if not item:
		logger.warning(
			f"SKU not found: {sku}",
			extra={"request_id": request.state.request_id, "sku": sku},
		)
		raise HTTPException(status_code=404, detail="SKU not found")
	return item


async def get_pending_change(db: AsyncSession, operation_id: str) -> PendingChange:
	stmt = lambda_stmt(
		lambda: select(PendingChange).where(PendingChange.operation_id == operation_id)
	)
	result = await db.execute(stmt)
	change = result.scalar_one_or_none()
	if not change:
		raise HTTPException(status_code=404, detail="Operation not found")
	return change
