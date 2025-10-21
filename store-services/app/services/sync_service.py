import httpx

from auth.client import get_service_token
from common.schemas import UpdateInventory
from core.config import _env


async def push_inventory_update(update: UpdateInventory):
    token = await get_service_token()
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{_env.central_url}/inventory/update",
            json=update,
            headers=headers
        )
        response.raise_for_status()
        return response.json()
