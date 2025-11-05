from datetime import UTC, datetime
from logging import Logger
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.store import get_db
from app.common.schemas import InventoryResponse, UpdateInventory
from app.main import app
from app.models.models import Inventory, PendingChange

PATH = "app.api.store"
client = TestClient(app=app)


@pytest.mark.parametrize(
	"inventory_object, status_code, text",
	[
		(
			Inventory(
				id=1,
				sku="abc",
				name="dummy",
				quantity=1,
				version=1,
				updated_at=datetime.now(UTC),
			),
			200,
			"dummy",
		),
		(None, 404, "SKU not found"),
	],
)
@patch(f"{PATH}.logger", spec=Logger)
def test_get_inventory_success_and_not_found(
	logger_mock, inventory_object, status_code, text, db
):
	mock_result = Mock()
	mock_result.scalar_one_or_none.return_value = inventory_object
	db.execute.return_value = mock_result

	app.dependency_overrides[get_db] = lambda: db

	response = client.get("/v1/local/inventory/abc")
	assert response.status_code == status_code
	result = response.json()
	if response.status_code == 200:
		inventory_response = InventoryResponse(**result)
		assert inventory_response.name == text
	else:
		assert result["detail"] == "SKU not found"
	app.dependency_overrides.clear()


@patch(f"{PATH}.logger", spec=Logger)
def test_get_inventory_500_error(mock_logger, db):
	mock_result = Mock()
	mock_result.scalar_one_or_none.side_effect = Exception()
	db.execute.return_value = mock_result

	app.dependency_overrides[get_db] = lambda: db

	response = client.get("/v1/local/inventory/abc")
	assert response.status_code == 500
	result = response.json()
	assert result["detail"] == "Internal server error while retrieving inventory"
	app.dependency_overrides.clear()


@patch(f"{PATH}.logger", spec=Logger)
def test_update_inventory_0_quantity(mock_logger, db):
	mock_result = Mock()
	mock_result.scalar_one_or_none.return_value = Inventory(
		id=1,
		sku="abc",
		name="dummy",
		quantity=0,
		version=1,
		updated_at=datetime.now(UTC),
	)
	db.execute.return_value = mock_result
	app.dependency_overrides[get_db] = lambda: db
	payload = UpdateInventory(delta=-1, version=1, operation_id=str(uuid4()))
	response = client.post("/v1/local/inventory/abc/update", json=payload.model_dump())
	assert (
		response.json()["detail"] == "Insufficient quantity. Available: 0, requested: 1"
	)
	assert response.status_code == 400
	app.dependency_overrides.clear()


@patch(f"{PATH}.logger")
def test_update_inventory(mock_logger, db):
	mock_result = Mock()
	mock_result.scalar_one_or_none.return_value = Inventory(
		id=1,
		sku="abc",
		name="dummy",
		quantity=1,
		version=1,
		updated_at=datetime.now(UTC),
	)
	mock_result_get = Mock()
	mock_result_get.scalar_one.return_value = Inventory(
		id=1,
		sku="abc",
		name="dummy",
		quantity=0,
		version=2,
		updated_at=datetime.now(UTC),
	)
	db.execute.side_effect = [mock_result, None, mock_result_get]
	db.commit.side_effect = [AsyncMock(), AsyncMock()]
	db.add.return_value = Mock()
	app.dependency_overrides[get_db] = lambda: db
	payload = UpdateInventory(delta=-1, version=1, operation_id=str(uuid4()))
	response = client.post("/v1/local/inventory/abc/update", json=payload.model_dump())
	assert response.json()["sku"] == "abc"
	assert response.status_code == 200
	assert db.execute.call_count == 3
	app.dependency_overrides.clear()


@patch(f"{PATH}.logger")
@patch(f"{PATH}.local_updates_total.inc", side_effect=Exception())
def test_update_inventory_exception(mock_local_update, mock_logger, db):
	mock_result = Mock()
	mock_result.scalar_one_or_none.return_value = Inventory(
		id=1,
		sku="abc",
		name="dummy",
		quantity=1,
		version=1,
		updated_at=datetime.now(UTC),
	)
	mock_result_get = Mock()
	mock_result_get.scalar_one.return_value = Inventory(
		id=1,
		sku="abc",
		name="dummy",
		quantity=0,
		version=2,
		updated_at=datetime.now(UTC),
	)
	db.execute.side_effect = [mock_result, None, mock_result_get]
	db.commit.side_effect = [AsyncMock(), AsyncMock()]
	db.add.return_value = Mock()
	app.dependency_overrides[get_db] = lambda: db
	payload = UpdateInventory(delta=-1, version=1, operation_id=str(uuid4()))
	response = client.post("/v1/local/inventory/abc/update", json=payload.model_dump())
	assert response.json()["sku"] == "abc"
	assert response.status_code == 200
	assert db.execute.call_count == 3
	app.dependency_overrides.clear()


@patch(f"{PATH}.logger", spec=Logger)
def test_get_operation_id(mock_logger, db):
	mock_result = Mock()
	mock_result.first.return_value = PendingChange(
		id=1,
		operation_id="abc",
		inventory_id=1,
		sku="abc",
		delta=-1,
		local_version=2,
		central_version=1,
		status="pending",
		error=None,
		created_at=datetime.now(UTC),
		updated_at=datetime.now(UTC),
	)
	db.execute.return_value = mock_result
	app.dependency_overrides[get_db] = lambda: db
	response = client.get("/v1/local/inventory/abc/operation_id")
	assert response.json()["operation_id"] == "abc"
	assert response.status_code == 200
	app.dependency_overrides.clear()


@pytest.mark.parametrize(
	"status, error, result",
	[("pending", None, False), ("completed", None, True), ("failed", "Erorr", False)],
)
@patch(f"{PATH}.logger", spec=Logger)
def test_get_sync_status(mock_logger, status, error, result, db):
	mock_result = Mock()
	mock_result.scalar_one_or_none.return_value = PendingChange(
		id=1,
		operation_id="abc",
		inventory_id=1,
		sku="abc",
		delta=-1,
		local_version=2,
		central_version=1,
		status=status,
		error=error,
		created_at=datetime.now(UTC),
		updated_at=datetime.now(UTC),
	)
	db.execute.return_value = mock_result
	app.dependency_overrides[get_db] = lambda: db
	response = client.get("/v1/local/sync/status/abc")
	assert response.json()["ok"] == result
	assert response.status_code == 200
	app.dependency_overrides.clear()


@patch(f"{PATH}.logger", spec=Logger)
def test_trigger_sync_celery(mock_logger):
	with patch(f"{PATH}.process_pending_once_task.delay") as _task:
		_task.return_value = MagicMock()
		response = client.post("/v1/local/sync/trigger")
		result = response.json()
		assert response.status_code == 200
		assert result["ok"]
		assert result["message"] == "Sync enqueued via Celery"
		_task.assert_called_once()

@pytest.mark.xfail(reason="I don't know to make this test")
@patch(f"{PATH}.process_pending_once")
def test_trigger_sync_background(mock_process):
	mock_process.return_value = None
	with patch(f"{PATH}.trigger_sync.process_pending_once_task", False):
		response = client.post("/v1/local/sync/trigger")
		result = response.json()
		
		assert response.status_code == 200
		assert result["message"] == "Sync scheduled in background"
