from typing import TypedDict

import httpx

from core.config import get_settings
import jwt
from datetime import UTC, datetime

settings = get_settings()

class Token(TypedDict):
    access_token: str
    token_type: str

_token_cache: str | None = None


def get_expired_token(token: str)->bool:
    payload = jwt.decode(
            token,
            settings.jwt_secrets,
            algorithms=[settings.jwt_algorithm],
            audience="central-service",
        )
    if datetime.now(UTC) > datetime.fromtimestamp(payload["exp"], UTC):
            return False
    return True

async def get_service_token()->str:
    global _token_cache
    if _token_cache and not get_expired_token(_token_cache):
        return _token_cache
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{settings.central_url}auth/token",
            json={"service_name": settings.service_name, "service_secret": settings.services_secret}
        )
        r.raise_for_status()
        data: Token = r.json()
        _token_cache = data["access_token"]
        return _token_cache
