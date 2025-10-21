from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from status import Status


class UpdateInventory(BaseModel):
    sku: str
    delta: int = Field(..., description="Negative for reservation/sale; positive for restock")
    version: int

class GetDataFromSku(BaseModel):
    id: int
    quantity: int
    version: int
    model_config = ConfigDict(from_attributes=True)

class TxnLine(BaseModel):
    product_id: int
    sku: str
    delta: int = Field(..., description="Negative for reservation/sale; positive for restock")

class TxnPrepareRquest(BaseModel):
    txn_id: UUID
    store_id: int
    lines: list[TxnLine]
    metadata: dict | None = None

class TxnPrepareResponse(BaseModel):
    txn_id: UUID
    status: Status = Field(default=Status.success, example="prepared")
    reaseon: None | str = None

class TxnCommitRequest(BaseModel):
    txn_id: UUID
    store_id: int
    idempotency_key: None | str = None

class TxnCommitResponse(BaseModel):
    txn_id: UUID
    status: Status = Field(Status.commited, example="commited")
    applied_at: datetime | None = None
    reason: str | None = None

class TxnAbortRequest(BaseModel):
    txn_id: UUID
    store_id: int
    reason: str | None = None

class GenericResponse(BaseModel):
    ok: bool
    message: str
