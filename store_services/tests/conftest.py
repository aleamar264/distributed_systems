import os
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings


@pytest.fixture
def db():
	return AsyncMock(spec=AsyncSession)


@pytest.fixture(autouse=True)
def override_settings():
	os.environ["JWT_SECRET"] = "dummy-secret"
	os.environ["SERVICE_NAME"] = "dummy-store"
	os.environ["SERVICE_SECRET"] = "other-dummy-secret"
	os.environ["CENTRAL_URL"] = "http://dummy-central"
	os.environ["DATABASE_URL"] = "sqlitesqlite+aiosqlite:///./dummy.db"
	os.environ["RABBITMQ_URL"] = "amqp://dummy-rabbit"
	get_settings()
	yield
	del os.environ["JWT_SECRET"]
	del os.environ["SERVICE_NAME"]
	del os.environ["SERVICE_SECRET"]
	del os.environ["CENTRAL_URL"]
	del os.environ["DATABASE_URL"]
	del os.environ["RABBITMQ_URL"]


@pytest.fixture(autouse=True)
def reset_patches():
	"""Ensure all patches are cleaned up between tests"""
	yield
	patch.stopall()


@pytest.fixture(autouse=True)
def reset_cache_get_service_token():
	"""Ensure all patches are cleaned up between tests"""
	import app.auth.client

	app.auth.client._token_cache = None
	yield
	app.auth.client._token_cache = None
