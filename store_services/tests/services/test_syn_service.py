from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from app.models.models import Inventory, PendingChange, SyncStatus
from app.services.sync_service import (
	process_change,
	process_pending_once,
	push_inventory_update,
	update_metrics,
	with_retry,
)
from sqlalchemy.ext.asyncio import AsyncSession

PATH_TO_SYNC_SERVICES = "app.services.sync_service"


@pytest.mark.asyncio
async def test_with_retry_success():
	mock_response = AsyncMock(spec=httpx.Response)
	mock_response.status_code = 200
	mock_func = AsyncMock(return_value=mock_response)

	result = await with_retry(mock_func)
	assert result == mock_response
	assert mock_func.call_count == 1


@pytest.mark.asyncio
async def test_with_retry_error_409():
	# mock_response = AsyncMock(spec=httpx.Response)

	mock_func = AsyncMock(
		side_effect=httpx.HTTPStatusError(
			response=Mock(status_code=409), request=Mock(), message="Dummy Error"
		)
	)
	with pytest.raises(httpx.HTTPStatusError) as err:
		result = await with_retry(mock_func, max_retries=1)
		assert result == ""
	assert err.value.response.status_code == 409


@pytest.mark.asyncio
async def test_with_retry_error_400_500():
	# mock_response = AsyncMock(spec=httpx.Response)

	mock_func = AsyncMock(
		side_effect=httpx.HTTPStatusError(
			response=Mock(status_code=401), request=Mock(), message=""
		)
	)
	with pytest.raises(httpx.HTTPStatusError) as err:
		result = await with_retry(mock_func)
	assert err.value.response.status_code == 401


@pytest.mark.asyncio
async def test_with_retry_eventual_success():
	mock_response = AsyncMock(spec=httpx.Response)
	mock_response.status_code = 200
	mock_func = AsyncMock(side_effect=[Exception("Temporary error"), mock_response])

	result = await with_retry(mock_func, max_retries=2)
	assert result == mock_response
	assert mock_func.call_count == 2


@pytest.mark.asyncio
async def test_with_retry_permanent_failure():
	mock_func = AsyncMock(side_effect=Exception("Permanent error"))

	with pytest.raises(Exception) as exc_info:
		await with_retry(mock_func, max_retries=2)
	assert str(exc_info.value) == "Permanent error"
	assert mock_func.call_count == 2


@pytest.mark.asyncio
@patch(f"{PATH_TO_SYNC_SERVICES}.get_service_token")
@patch(
	f"{PATH_TO_SYNC_SERVICES}.get_inventory",
	return_value=Inventory(
		id=1, sku="abc", name="abc", quantity=1, version=1, updated_at=datetime.now(UTC)
	),
)
@patch(
	f"{PATH_TO_SYNC_SERVICES}.update_model",
	return_value=Inventory(
		id=1, sku="abc", name="abc", quantity=1, version=1, updated_at=datetime.now(UTC)
	),
)
async def test_push_inventory_update_success(mock_token, override_settings, db):
	mock_token.return_value = "test_token"
	mock_response = AsyncMock(spec=httpx.Response)
	mock_response.status_code = 200
	mock_response.json.return_value = {"version": "2"}

	mocked_client = AsyncMock()
	mocked_client.post.return_value = mock_response

	change = PendingChange(
		sku="test-sku", operation_id="test-op", inventory_id=1, delta=5
	)

	with patch(f"{PATH_TO_SYNC_SERVICES}.httpx.AsyncClient") as mock_client:
		mock_client.return_value.__aenter__.return_value = mocked_client
		success, error = await push_inventory_update(db=db, change=change)

	assert success
	assert error is None


@pytest.mark.asyncio
@patch(
	f"{PATH_TO_SYNC_SERVICES}.get_service_token",
	side_effect=httpx.HTTPStatusError(message="Error", request=Mock(), response=Mock()),
)
async def test_push_inventory_update_failed_token(mock_token, override_settings, db):
	success, error = await push_inventory_update(db=db, change=PendingChange())
	assert not success
	assert error == "HTTP error: Error"


@pytest.mark.asyncio
@patch(
	f"{PATH_TO_SYNC_SERVICES}.count",
	side_effect=[1, 1],
)
async def test_update_metrics(db):
	with (
		patch(f"{PATH_TO_SYNC_SERVICES}.inventory_count") as mock_inv_count,
		patch(f"{PATH_TO_SYNC_SERVICES}.pending_changes_gauge") as mock_pending_gauge,
	):
		await update_metrics(db)
	mock_inv_count.set.assert_called()
	mock_pending_gauge.set.assert_called_once()
	mock_pending_gauge.set.assert_called_once_with(1)
	mock_inv_count.set.assert_called_once_with(1)


@pytest.mark.asyncio
@patch(f"{PATH_TO_SYNC_SERVICES}.update_model", side_effect=[None, None])
async def test_process_change_success(db):
	change = PendingChange(
		id=1,
		sku="test-sku",
		operation_id="test-op",
		inventory_id=1,
		status=SyncStatus.PENDING,
	)
	with patch(f"{PATH_TO_SYNC_SERVICES}.push_inventory_update") as mock_push:
		mock_push.return_value = (True, None)
		result = await process_change(db, change)

		assert result is True


@pytest.mark.asyncio
@patch(f"{PATH_TO_SYNC_SERVICES}.update_model", side_effect=[None, None])
async def test_process_change_failure(db):
	change = PendingChange(
		id=1,
		sku="test-sku",
		operation_id="test-op",
		inventory_id=1,
		status=SyncStatus.PENDING,
	)

	with patch(f"{PATH_TO_SYNC_SERVICES}.push_inventory_update") as mock_push:
		mock_push.return_value = (False, "Test error")
		result = await process_change(db, change)

		assert result is True  # Process completed, even though sync failed


@pytest.mark.asyncio
@patch(f"{PATH_TO_SYNC_SERVICES}.update_model", side_effect=[None, None, None])
@patch(f"{PATH_TO_SYNC_SERVICES}.push_inventory_update")
async def test_process_change_failure_exception(mock_update_model, mock_push, db):
	change = PendingChange(
		id=1,
		sku="test-sku",
		operation_id="test-op",
		inventory_id=1,
		status=SyncStatus.PENDING,
	)
	mock_push.side_effect = Exception()
	with pytest.raises(Exception) as err:
		result = await process_change(db, change)
		assert result is False


@pytest.mark.asyncio
@patch(f"{PATH_TO_SYNC_SERVICES}.session")
@patch(f"{PATH_TO_SYNC_SERVICES}.get_pending_changes", return_value = [])
@patch(f"{PATH_TO_SYNC_SERVICES}.update_metrics", return_value=None)
async def test_process_pending_once_empty(
	mock_update_metrics, mock_pending_changes, db_with
):
    session_mock = AsyncMock(spec=AsyncSession)
    db_cm = AsyncMock()
    db_cm.__aenter__.return_value = session_mock
    db_cm.__aexit__.return_value = None
    db_with = db_cm
    result = await process_pending_once()
    assert result == 0


@pytest.mark.asyncio
@patch(f"{PATH_TO_SYNC_SERVICES}.get_pending_changes")
@patch(f"{PATH_TO_SYNC_SERVICES}.update_metrics", return_value=None)
@patch(f"{PATH_TO_SYNC_SERVICES}.process_change")
@patch(f"{PATH_TO_SYNC_SERVICES}.sync_duration_seconds.set")
@patch(f"{PATH_TO_SYNC_SERVICES}.session")
async def test_process_pending_once_success(
	db_with,
	mock_sync_duration,
	mock_process_change,
	mock_update_metrics,
	mock_pending_changes,
):
	# Create test changes
    changes = [
        PendingChange(
            sku=f"test-sku-{i}",
            operation_id=f"test-op-{i}",
            inventory_id=1,
            status=SyncStatus.PENDING,
        )
        for i in range(3)
    ]
    mock_pending_changes.return_value = changes
    mock_process_change.side_effect = [
        True,
        True,
        True,
    ]  # Like it's success and only 3 changes
    session_mock = AsyncMock(spec=AsyncSession)

    # Create the context manager mock
    db_cm = AsyncMock()
    db_cm.__aenter__.return_value = session_mock
    db_cm.__aexit__.return_value = None
    db_with = db_cm


    processed = await process_pending_once()

    assert processed == 3
    assert mock_process_change.call_count == 3


@pytest.mark.asyncio
@patch(f"{PATH_TO_SYNC_SERVICES}.get_pending_changes")
@patch(f"{PATH_TO_SYNC_SERVICES}.update_metrics", return_value=None)
@patch(f"{PATH_TO_SYNC_SERVICES}.process_change")
@patch(f"{PATH_TO_SYNC_SERVICES}.sync_duration_seconds.set")
@patch(f"{PATH_TO_SYNC_SERVICES}.session")
async def test_process_pending_once_partial_success(
	db_with,
	mock_sync_duration,
	mock_process_change,
	mock_update_metrics,
	mock_pending_changes,
):
	# Create test changes
	changes = [
		PendingChange(
			sku=f"test-sku-{i}",
			operation_id=f"test-op-{i}",
			inventory_id=1,
			status=SyncStatus.PENDING,
		)
		for i in range(3)
	]

	mock_pending_changes.return_value = changes
	mock_process_change.side_effect = [
		True,
		False,
		True,
	]  # Like it's success and only 3 changes
	session_mock = AsyncMock(spec=AsyncSession)

	# Create the context manager mock
	db_cm = AsyncMock()
	db_cm.__aenter__.return_value = session_mock
	db_cm.__aexit__.return_value = None
	db_with = db_cm
	processed = await process_pending_once()

	assert processed == 2
	assert mock_process_change.call_count == 3
