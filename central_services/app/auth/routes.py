from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_db
from models.models import ServiceCredentials

from .schemas import TokenRequest, TokenResponse
from .utils import create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])



@router.post("/token", response_model=TokenResponse)
async def get_token(payload: TokenRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ServiceCredentials).where(
            ServiceCredentials.service_name == payload.service_name,
            ServiceCredentials.service_secret == payload.service_secret
        )
    )
    service = result.scalar_one_or_none()
    if not service:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token({
        "iss": service.service_name,
        "sub": service.service_name,
        "role": service.role
    })
    return TokenResponse(access_token=token, token_type="bearer")
