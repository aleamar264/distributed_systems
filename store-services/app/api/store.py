from typing import Annotated
from uuid import UUID

import httpx
from common.schemas import (
    GenericResponse,
    Inventory,
    TxnAbortRequest,
    TxnCommitRequest,
    TxnCommitResponse,
    TxnPrepareResponse,
    TxnPrepareRquest,
)
from fastapi import APIRouter, Header
from pydantic import BaseModel, Field

router = APIRouter(prefix="/store", tags=["store"])

class Headers(BaseModel):
    idempotency_key: str = Field(..., alias="Idempotency-Key")
    authorization: str = Field(..., alias="Authorization")

@router.get("/inventory/{sku}", response_model=Inventory)
async def get_inventory(sku: str)->Inventory:
    """Return local inventory"""
    raise NotImplementedError

@router.post("/inventory/update", response_model=TxnPrepareResponse)
async def inventory_update(payload: TxnPrepareRquest,
    header: Annotated[Headers, Header()])->TxnPrepareResponse:
    """
    Initiates 2PC:
     1. Write PREPARE local intent (do NOT commit).
     2. Call central /txn/prepare.
     3. If central returns 'prepared': mark local prepared and respond prepared.
     4. If central aborts: rollback local intent and respond abort.
    """
    raise NotImplementedError

@router.post("/txn/commit-local", response_model=TxnCommitResponse)
async def commit_local(payload: TxnCommitRequest,idempotency_key: str = Header(..., alias="Idempotency-Key")
    ):
    """Start transactional update (initiates 2PC prepare with Central)
    Called after central confirms commit. Commit the local transaction atomically.
    """
    raise NotImplementedError

@router.post("/txn/abort-local", response_model=GenericResponse)
async def abort_local(payload: TxnAbortRequest):
    """
    Undo any prepared local state.
    """
    raise NotImplementedError