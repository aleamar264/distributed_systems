from datetime import UTC, datetime, timedelta
import os
from unittest.mock import patch, AsyncMock, Mock

from fastapi import HTTPException, Header, status
from fastapi.security import HTTPAuthorizationCredentials
import jwt
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.utils import create_access_token, verify_service_jwt
from app.models.models import ServiceCredentials
from pydantic import BaseModel


class DummyHttpAuth(BaseModel):
    scheme: str
    credentials: str

def test_create_access_token():
    os.environ['JWT_SECRET'] = 'my_value'
    token = create_access_token(data={"iss":"dummy", "sub":"", "role":"services"})
    assert token


@pytest.mark.asyncio
async def test_verify_service_jwt_success():
    # create a token signed with the service secret
    service_secret = "svc-secret"
    expire = datetime.now(UTC) + timedelta(hours=1)
    payload = {"iss": "dummy", "sub": "sub", "role": "store", "exp": expire, "aud": "central-service"}
    token = HTTPAuthorizationCredentials(credentials=jwt.encode(payload, service_secret, algorithm="HS256"), scheme="Bearer")

    # prepare mock db to return a ServiceCredentials with matching secret
    service = ServiceCredentials(id=1, service_name="dummy", service_secret=service_secret, role="store")
    mock_result = Mock()
    mock_result.scalar_one_or_none.return_value = service
    db = AsyncMock(spec=AsyncSession)
    db.execute.return_value = mock_result

    result = await verify_service_jwt(db=db, token=token)
    assert result["service_name"] == "dummy"
    assert result["role"] == "store"


@pytest.mark.asyncio
async def test_verify_service_jwt_unknown_service():
    secret = "any-secret"
    expire = datetime.now(UTC) + timedelta(hours=1)
    payload = {"iss": "unknown-svc", "sub": "x", "role": "r", "exp": expire, "aud": "central-service"}
    token = HTTPAuthorizationCredentials(credentials=jwt.encode(payload, secret, algorithm="HS256"), scheme="Bearer")

    mock_result = Mock()
    mock_result.scalar_one_or_none.return_value = None
    db = AsyncMock(spec=AsyncSession)
    db.execute.return_value = mock_result

    with pytest.raises(HTTPException) as exc:
        await verify_service_jwt(db=db, token=token)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_verify_service_jwt_invalid_signature():
    # token signed with a different secret than the one stored in ServiceCredentials -> invalid signature
    real_secret = "real-secret"
    bad_secret = "bad-secret"
    expire = datetime.now(UTC) + timedelta(hours=1)
    payload = {"iss": "dummy", "sub": "s", "role": "r", "exp": expire, "aud": "central-service"}
    token = HTTPAuthorizationCredentials(credentials=jwt.encode(payload, bad_secret, algorithm="HS256"), scheme="Bearer")


    service = ServiceCredentials(id=1, service_name="dummy", service_secret=real_secret, role="store")
    mock_result = Mock()
    mock_result.scalar_one_or_none.return_value = service
    db = AsyncMock(spec=AsyncSession)
    db.execute.return_value = mock_result

    with pytest.raises(HTTPException) as exc:
        await verify_service_jwt(db=db, token=token)
    assert exc.value.status_code == 401

