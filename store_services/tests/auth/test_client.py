from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from app.auth.client import get_service_token


@pytest.mark.asyncio
@patch("app.auth.client._token_cache", "some-dummy-token")
async def test_get_service_token_token_cache(override_settings):
	token = await get_service_token()
	assert token == "some-dummy-token"


@pytest.mark.asyncio
@patch("app.auth.client.httpx.AsyncClient")
async def test_get_service_token(MockAsyncHttp, override_settings):
	mock_response = Mock()
	mock_response.status_code = 200
	mock_response.json.return_value = {
		"access_token": "some-dummy-token",
		"token_type": "bearer",
	}
	mocked_async_client = AsyncMock()
	mocked_async_client.post = AsyncMock(return_value=mock_response)
	MockAsyncHttp.return_value.__aenter__.return_value = mocked_async_client
	token = await get_service_token()
	assert token == "some-dummy-token"


@pytest.mark.asyncio
@patch("app.auth.client.httpx.AsyncClient")
async def test_get_service_token_raise_status(MockAsyncHttp, override_settings):
	mocked_async_client = AsyncMock()
	mocked_async_client.post = AsyncMock(
		side_effect=httpx.HTTPStatusError(
			message="Error",
			request=Mock(spec=httpx.Request),
			response=Mock(httpx.Response, status_code=500),
		)
	)

	MockAsyncHttp.return_value.__aenter__.return_value = mocked_async_client
	with pytest.raises(httpx.HTTPStatusError):
		await get_service_token()
