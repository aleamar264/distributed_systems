from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from typing import Annotated, TypedDict

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from core.db import session
from models.models import ServiceCredentials

security = HTTPBearer()
settings = get_settings()

class Token(TypedDict):
    iss: str
    sub: str
    role: str


class VerifiedService(TypedDict):
    service_name: str
    role: str


async def get_db() -> AsyncGenerator[AsyncSession]:
    async with session() as db:
        yield db


async def verify_service_jwt(
    db: Annotated[AsyncSession, Depends(get_db)],
    token: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> VerifiedService:
    """Verify JWT is signed by a known service and return the service details."""
    credentials_exception = HTTPException(
		status_code=status.HTTP_401_UNAUTHORIZED,
		detail="Could not validate credentials",
		headers={"WWW-Authenticate": "Bearer"},
	)
    try:
    # First decode without verification to get issuer
        unverified = jwt.decode(token.credentials, options={"verify_signature": False})
        service_name = unverified.get("iss")
        if not service_name:
            raise HTTPException(401, "Missing issuer claim")

        # Look up service secret
        result = await db.execute(
            select(ServiceCredentials).where(ServiceCredentials.service_name == service_name)
        )
        service = result.scalar_one_or_none()
        if not service:
            raise HTTPException(401, "Unknown service")
        payload = jwt.decode(
            token.credentials,
            settings.jwt_secrets,
            algorithms=[settings.jwt_algorithm],
            audience="central-service",
        )
        if datetime.now(UTC) > datetime.fromtimestamp(payload["exp"], UTC):
            raise credentials_exception
        return {"service_name": service_name, "role": service.role}
    except jwt.InvalidTokenError as e:
        raise credentials_exception from e


def create_access_token(data: Token) -> str:
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(minutes=settings.jwt_expiration)
    to_encode.update({"exp": expire, "aud": "central-service"})
    return jwt.encode(to_encode, settings.jwt_secrets, algorithm=settings.jwt_algorithm)
