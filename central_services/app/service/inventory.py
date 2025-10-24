from datetime import UTC, datetime, timedelta
import logging
from typing import Any

from fastapi import HTTPException
from sqlalchemy import lambda_stmt, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from common.schemas import (
	ConflictError,
	GetDataFromSku,
	InventoryResponse,
	UpdateInventory,
)
from models.models import IdempotencyKey, Inventory
from observability import (
	inventory_update_conflicts_total,
	inventory_update_failures_total,
)


logger = logging.getLogger("central_service")
async def get_data_from_sku(sku: str, db: AsyncSession) -> GetDataFromSku:
	"""Get data from sku. The data retrieve is the id, quantity and version of the Inventory
	Params:
		sku (str): Identifier of the Inventory
		db (AsyncSession)

	Return:
		GetDataFromSku

	Raises:
		HTTPException
	"""
	stmt = lambda_stmt(
		lambda: select(Inventory.id, Inventory.quantity, Inventory.version).where(
			Inventory.sku == sku
		)
	)
	result = await db.execute(stmt)
	item = result.first()
	if not item:
		raise HTTPException(404, "Item not found")
	return GetDataFromSku(**item._asdict())


async def update_inventory(db: AsyncSession, sku: str, update_values: dict) -> None:
	"""Update the Inventory given a specific sku
	Params:
		sku (str): Identifier of the Inventory
		update_values (dict): Dictionary with the values to update
		db (AsyncSession)

	Return:
		None
	"""
	stmt = update(Inventory).where(Inventory.sku == sku).values(**update_values)
	await db.execute(stmt)
	await db.commit()


async def get_item_from_sku(
	db: AsyncSession, sku: str, retrieve_for_update: bool = False
) -> Inventory:
	"""Get all the item from a single sku
	Params:
		sku (str): Identifier of the Inventory
		db (AsyncSession)
		retrieve_for_update (bool): Flag to lock the row to retrieve for further actions

	Return:
		Inventory

	Raises:
		HTTPEXception
	"""
	stmt = lambda_stmt(lambda: select(Inventory).where(Inventory.sku == sku))
	if retrieve_for_update:
		stmt += lambda s: s.with_for_update()
	result = await db.execute(stmt)
	item = result.scalar_one_or_none()
	if not item:
		raise HTTPException(status_code=404, detail="SKU not found")
	return item


async def create_idempotency(db:AsyncSession, idempotency: IdempotencyKey):
	db.add(idempotency)
	await db.commit()

async def get_idempotency(
	idempotency_key: str, service_name: str, db: AsyncSession
) -> IdempotencyKey | None:
	"""Get the row that contain the IdempotencyKey.
	Params:
		idempotency_key (str): Key to search
		service_name (str): Name of the services that is making the
		requirement
		db (AsyncSession)

	Return:
		IdempotencyKey | None"""
	now = datetime.now(UTC)
	stmt = lambda_stmt(
		lambda: select(IdempotencyKey).where(
			IdempotencyKey.key == idempotency_key,
			IdempotencyKey.service_name == service_name,
			IdempotencyKey.expires_at > now,
		)
	)
	idem_key = await db.execute(stmt)
	return idem_key.scalar_one_or_none()


async def update_idempotency(
	db: AsyncSession, idempotency_key: str, update_values: dict[str, Any]
):
	"""Update the Idempotency table given a specific key
	Params:
		idempotency_key (str): Identifier of the Idempotency table
		update_values (dict): Dictionary with the values to update
		db (AsyncSession)

	Return:
		None
	"""
	await db.execute(
		update(IdempotencyKey)
		.where(IdempotencyKey.key == idempotency_key)
		.values(**update_values)
	)
	await db.commit()


async def update_inventory_return(
	db: AsyncSession, sku: str, version: int, update_values: dict
) -> Inventory:
	result = await db.execute(
		update(Inventory)
		.where(Inventory.sku == sku, Inventory.version == version)
		.values(**update_values)
		.returning(Inventory)
	)
	await db.commit()
	return result.scalar_one()


async def adjust_inventory_services(
	db: AsyncSession,
	payload: UpdateInventory,
	sku: str,
	service_name: str,
	idempotency_key: str,
) -> Inventory:
	# Get current item state
	item = await get_item_from_sku(db=db, retrieve_for_update=True, sku=sku)
	logger.info(f"Item version:{item.version}")
	logger.info(f"Payload version {payload.version}")
	if item.version != payload.version:
		inventory_update_conflicts_total.inc()
		raise HTTPException(
			status_code=409,
			detail=ConflictError(
				message="Optimistic lock failed - item was updated",
				current_state=InventoryResponse.model_validate(item),
			).model_dump(),
		)

	new_qty = item.quantity + payload.delta
	logger.info(f"New qty: {new_qty}")
	if new_qty < 0:
		inventory_update_failures_total.inc()
		raise HTTPException(
			status_code=400,
			detail=f"Insufficient quantity. Available: {item.quantity}, requested: {abs(payload.delta)}",
		)

	updated = await update_inventory_return(
		db=db,
		sku=sku,
		version=payload.version,
		update_values={
			"quantity": new_qty,
			"version": payload.version + 1,
			"updated_at": datetime.now(UTC),
		},
	)
	logger.info(f"vesion: {updated.version}, qty: {updated.quantity}")
	# Store idempotency key (upsert-like behavior)
	await update_idempotency(
		db=db,
		idempotency_key=idempotency_key,
		update_values={
			"service_name": service_name,
			"request_hash": hash(payload.model_dump_json()),
			"response_body": hash(
				InventoryResponse.model_validate(updated).model_dump_json()
			),
			"expires_at": datetime.now(UTC) + timedelta(hours=24),
		},
	)

	await db.commit()
	return updated
