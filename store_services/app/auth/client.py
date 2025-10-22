import httpx

from core.config import _env

_token_cache: str | None = None
async def get_service_token()->str:
    global _token_cache
    if _token_cache:
        return _token_cache
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{_env.central_url}/auth/token",
            json={"service_name": _env.service_name, "service_secrets": _env.services_secret}
        )
        r.raise_for_status()
        data = r.json()
        _token_cache = data["access_token"]
        return _token_cache
