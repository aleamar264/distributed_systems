from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
def db():
	return AsyncMock(spec=AsyncSession)

@pytest.fixture
def db_with():
	"""Db with Context Manager"""
	session_mock = AsyncMock(spec=AsyncSession)

	# Create the context manager mock
	db_cm = AsyncMock()
	db_cm.__aenter__.return_value = session_mock
	db_cm.__aexit__.return_value = None

	return db_cm, session_mock
