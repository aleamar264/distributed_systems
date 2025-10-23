from typing import TypedDict

import httpx

from core.config import get_settings

settings = get_settings()

class Token(TypedDict):
    access_token: str
    token_type: str

_token_cache: str | None = None

async def get_service_token()->str:
    global _token_cache
    if _token_cache:
        return _token_cache
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{settings.central_url}/auth/token",
            json={"service_name": settings.service_name, "service_secrets": settings.services_secret}
        )
        r.raise_for_status()
        data: Token = r.json()
        _token_cache = data["access_token"]
        return _token_cache
