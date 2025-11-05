from collections.abc import Sequence
from datetime import UTC, datetime
from unittest.mock import Mock, patch
from fastapi import HTTPException
import pytest

from app.models.models import Inventory, PendingChange, SyncStatus
from app.services.sync_service_db import (
	count,
	get_inventory,
	get_pending_change_by_sku,
	get_pending_changes,
	update_model,
)


@pytest.mark.asyncio
async def test_get_inventory(db):
	mock_result = Mock()
	mock_result.scalar_one.return_value = Inventory()
	db.execute.return_value = mock_result
	await get_inventory(id=1, db=db)
	mock_result.scalar_one.assert_called_once()
	db.execute.assert_called_once()


@pytest.mark.asyncio
async def test_update_model(db):
	db.execute.return_value = None
	await update_model(id=1, db=db, update_values={}, model=Inventory)
	db.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_pending_change(db):
	mock_result = Mock()
	mock_result.scalars.return_value.all.return_value = [Inventory(), Inventory()]
	db.execute.return_value = mock_result
	result = await get_pending_changes(db=db, status=SyncStatus.COMPLETED)
	mock_result.scalars.assert_called_once()
	db.execute.assert_called_once()
	assert len(result) == 2


@pytest.mark.asyncio
async def test_get_pending_change_by_sku_no_item(db):
	mock_result = Mock()
	mock_result.first.return_value = None
	db.execute.return_value = mock_result
	with pytest.raises(HTTPException) as err:
		await get_pending_change_by_sku(db=db, sku="abc")
		mock_result.first.assert_called_once()
		db.execute.assert_called_once()
	assert err.value.detail == "No item for change for SKU abc"


@pytest.mark.asyncio
async def test_get_pending_change_by_sku(db):
	mock_result = Mock()
	mock_result.first.return_value = PendingChange(
		operation_id="abcd",
		sku="abc",
		delta=0,
		local_version=1,
		central_version=1,
		status="pending",
		error=None,
		created_at=datetime.now(UTC),
		updated_at=datetime.now(UTC),
	)
	db.execute.return_value = mock_result
	result = await get_pending_change_by_sku(db=db, sku="abc")
	assert result == "abcd"
	mock_result.first.assert_called_once()
	db.execute.assert_called_once()

@pytest.mark.asyncio
async def test_count(db):
    with patch("app.services.sync_service_db.func.count", return_value=1):
        mock_result = Mock()
        mock_result.scalar_one.return_value = 1
        db.execute.return_value = mock_result
        result = await count(db=db, model=Inventory)
        assert result == 1