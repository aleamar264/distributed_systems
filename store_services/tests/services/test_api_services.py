from logging import Logger
from unittest.mock import Mock

import pytest
from fastapi import HTTPException, Request

from app.models.models import Inventory, PendingChange
from app.services.api_services import get_inventory_by_sku, get_pending_change


@pytest.mark.asyncion
async def test_inventory_by_sku_no_item(db):
	fake_logger = Mock(spec=Logger)
	fake_request = Mock(spec=Request)
	mock_result = Mock()
	mock_result.scalar_one_or_none.return_value = None
	db.execute.return_value = mock_result
	with pytest.raises(HTTPException) as err:
		await get_inventory_by_sku(
			sku="abc",
			db=db,
			logger=fake_logger,
			request=fake_request,
			wait_update=False,
		)
	assert err.value.detail == "SKU not found"


@pytest.mark.asyncion
async def test_inventory_by_sku(db):
	fake_logger = Mock(spec=Logger)
	fake_request = Mock(spec=Request)
	mock_result = Mock()
	mock_result.scalar_one_or_none.return_value = Inventory()
	db.execute.return_value = mock_result

	await get_inventory_by_sku(
		sku="abc",
		db=db,
		logger=fake_logger,
		request=fake_request,
		wait_update=False,
	)
	fake_logger.assert_not_called()
	fake_request.assert_not_called()
	mock_result.scalar_one_or_none.assert_called_once()

@pytest.mark.asyncion
async def test_inventory_by_sku_with_update(db):
	fake_logger = Mock(spec=Logger)
	fake_request = Mock(spec=Request)
	mock_result = Mock()
	mock_result.scalar_one_or_none.return_value = Inventory()
	db.execute.return_value = mock_result

	await get_inventory_by_sku(
		sku="abc",
		db=db,
		logger=fake_logger,
		request=fake_request,
		wait_update=True,
	)
	fake_logger.assert_not_called()
	fake_request.assert_not_called()
	mock_result.scalar_one_or_none.assert_called_once()


@pytest.mark.asyncio
async def test_get_pending_change_raise(db):
    mock_result = Mock()
    mock_result.scalar_one_or_none.return_value = None
    db.execute.return_value = mock_result
    with pytest.raises(HTTPException) as err:
        await get_pending_change(db=db, operation_id="abc")
    assert err.value.detail == "Operation not found"


@pytest.mark.asyncio
async def test_get_pending_change(db):
    mock_result = Mock()
    mock_result.scalar_one_or_none.return_value = PendingChange()
    db.execute.return_value = mock_result
    result = await get_pending_change(db=db, operation_id="abc")
    assert isinstance(result, PendingChange)
    mock_result.scalar_one_or_none.assert_called_once()
    db.execute.assert_called()