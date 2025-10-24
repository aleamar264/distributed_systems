from datetime import UTC, datetime
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
import pytest
from app.common.schemas import InventoryResponse
from app.main import app
from app.models.models import Inventory



PREFIX = "/v1/local"
API_PATH = "app.api.store"



@patch(
	f"{API_PATH}.get_inventory_by_sku", Inventory(
		id=1, sku="abc", name="def", quantity=1, version=1, updated_at=datetime.now(UTC)
	))
def test_get_inventory(mock_get_inventory,auth_token, db):
	app.dependency_overrides["get_db"] = db
	response = client.get(f"{PREFIX}/inventory/abc", headers={"Authorization": "Bearer {auth_token}"})
	assert response.status_code == 200
