from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class UpdateInventory(BaseModel):
    sku: str
    delta: int = Field(..., description="Negative for reservation/sale; positive for restock")
    version: int
    operation_id: str = Field(..., description="Client-generated operation ID for idempotency")

class UpdateInventoryResponse(BaseModel):
    sku: str
    quantity: int
    vesion: int

class InventoryResponse(BaseModel):
    sku: str
    name: str
    quantity: int
    version: int
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    model_config = ConfigDict(from_attributes=True)


class ConflictError(BaseModel):
    error: Literal["CONFLICT"] = "CONFLICT"
    message: str
    current_state: InventoryResponse


class BulkSyncRequest(BaseModel):
    items: list[UpdateInventory]

class GetDataFromSku(BaseModel):
    id: int
    quantity: int
    version: int
    model_config = ConfigDict(from_attributes=True)


class GenericResponse(BaseModel):
    ok: bool
    message: str
