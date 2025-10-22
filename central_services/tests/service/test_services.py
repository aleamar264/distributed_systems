from collections import namedtuple
from datetime import UTC, datetime, timedelta
from re import A
from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy import Row
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.schemas import InventoryResponse, UpdateInventory
from app.models.models import IdempotencyKey, Inventory
from app.service.inventory import (
	adjust_inventory_services,
	get_data_from_sku,
	get_idempotency,
	get_item_from_sku,
	update_idempotency,
	update_inventory,
	update_inventory_return,
)

fake_row = namedtuple("Row", ["id", "quantity", "version"])


@pytest.mark.asyncio
@pytest.mark.parametrize("item", [None, fake_row(id=1, version=1, quantity=1)])
async def test_get_data_from_sku(db: AsyncSession, item: None | Row):
	mock_result = Mock()
	mock_result.first.return_value = item
	db.execute.return_value = mock_result
	if item is None:
		with pytest.raises(HTTPException) as err:
			await get_data_from_sku(db=db, sku="abc")
		assert err.type == HTTPException
		assert err.value.status_code == 404
		assert err.value.detail == "Item not found"
	if item is not None:
		result = await get_data_from_sku(db=db, sku="abc")
		assert result.id == item.id
		assert result.version == item.version


@pytest.mark.asyncio
async def test_update_inventory(db: AsyncSession):
	db.execute.return_value = Mock()
	update_values = update_values = {
		"quantity": 0,
		"version": 2,
		"updated_at": datetime.now(UTC),
	}
	await update_inventory(db=db, sku="abc", update_values=update_values)


@pytest.mark.asyncio
@pytest.mark.parametrize(
	("for_update", "item"),
	[
		(False, None),
		(
			False,
			Inventory(id=1, sku="abc", name="dummy", quantity=1, version=1),
		),
		(
			True,
			Inventory(id=1, sku="abc", name="dummy", quantity=1, version=1),
		),
	],
)
async def test_get_item_from_sku(
	db: AsyncSession, for_update: bool, item: Inventory | None
):
	mock_result = Mock()
	mock_result.scalar_one_or_none.return_value = item
	db.execute.return_value = mock_result
	if item is None:
		with pytest.raises(HTTPException) as err:
			await get_item_from_sku(db=db, sku="abc", retrieve_for_update=for_update)
		assert err.type == HTTPException
		assert err.value.status_code == 404
		assert err.value.detail == "SKU not found"
	if item is not None:
		result = await get_item_from_sku(
			db=db, sku="abc", retrieve_for_update=for_update
		)
		assert result.id == 1
		assert result.version == 1
		assert result.name == "dummy"
		# mock_result.assert_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
	"item",
	[
		None,
		IdempotencyKey(
			id=1, key="abc", service_name="dummy", request_hash="", response_body="{}"
		),
	],
)
async def test_get_idempotency(db: AsyncSession, item: None | IdempotencyKey):
	mock_result = Mock()
	mock_result.scalar_one_or_none.return_value = item
	db.execute.return_value = mock_result
	result = await get_idempotency(db=db, service_name="dummy", idempotency_key="abc")
	assert result == item
	if item is not None:
		assert result.key == item.key


@pytest.mark.asyncio
async def test_update_idempotency(db: AsyncSession):
	db.execute.return_value = Mock()
	update_values = {
		"service_name": "dummy-services",
		"request_hash": "{}",
		"response_body": "{}",
		"expires_at": datetime.now(UTC) + timedelta(hours=24),
	}
	await update_idempotency(db=db, idempotency_key="abc", update_values=update_values)


@pytest.mark.asyncio
async def test_update_inventory_return(db: AsyncSession):
	mock_result = Mock()
	mock_result.scalar_one.return_value = Inventory(
		id=1, sku="abc", name="dummy", quantity=2, version=2
	)
	db.execute.return_value = mock_result
	update_values = {"quantity": 2, "version": 2}
	result = await update_inventory_return(
		db=db, sku="abc", version=1, update_values=update_values
	)
	assert result.version == 2
	assert result.quantity == 2


@pytest.mark.asyncio
@patch(
	"app.service.inventory.get_item_from_sku",
	return_value=Inventory(
		id=1,
		sku="abc",
		name="dummy",
		quantity=2,
		version=2,
		updated_at=datetime.now(UTC),
	),
)
async def test_adjust_inventory_services_wrong_version(db: AsyncSession):
	with pytest.raises(HTTPException) as err:
		await adjust_inventory_services(
			db=db,
			payload=UpdateInventory(sku="abc", delta=1, version=3, operation_id="abcd"),
			sku="abc",
			service_name="dummy-service",
			idempotency_key="abc",
		)
	assert err.value.status_code == 409
	assert err.value.detail["message"] == "Optimistic lock failed - item was updated"
	assert err.value.detail["current_state"]["name"] == "dummy"


@pytest.mark.asyncio
@patch(
	"app.service.inventory.get_item_from_sku",
	return_value=Inventory(
		id=1,
		sku="abc",
		name="dummy",
		quantity=0,
		version=2,
		updated_at=datetime.now(UTC),
	),
)
async def test_adjust_inventory_services_less_stock(db: AsyncSession):
	with pytest.raises(HTTPException) as err:
		await adjust_inventory_services(
			db=db,
			payload=UpdateInventory(
				sku="abc", delta=-1, version=2, operation_id="abcd"
			),
			sku="abc",
			service_name="dummy-service",
			idempotency_key="abc",
		)
	assert err.value.status_code == 400
	assert err.value.detail == "Insufficient quantity. Available: 0, requested: 1"


@pytest.mark.asyncio
@patch(
	"app.service.inventory.get_item_from_sku",
	return_value=Inventory(
		id=1,
		sku="abc",
		name="dummy",
		quantity=1,
		version=2,
		updated_at=datetime.now(UTC),
	),
)
@patch(
	"app.service.inventory.update_inventory_return",
	return_value=Inventory(
		id=1,
		sku="abc",
		name="dummy",
		quantity=0,
		version=3,
		updated_at=datetime.now(UTC),
	),
)
@patch("app.service.inventory.update_idempotency",return_value= None)
async def test_adjust_inventory_services( get_item_mock, update_inventory_mock, update_idempotency_mock, db: AsyncSession):
	item = await adjust_inventory_services(
		db=db,
		payload=UpdateInventory(sku="abc", delta=-1, version=2, operation_id="abcd"),
		sku="abc",
		service_name="dummy-service",
		idempotency_key="abc",
	)
	assert item.version == 3
	assert item.quantity == 0
