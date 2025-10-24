from datetime import datetime
from uuid import uuid4
from pydantic import BaseModel, ConfigDict, Field


class Products(BaseModel):
    id: int
    sku: str
    name: str
    price: int

class UpdateInventory(BaseModel):
    delta: int = Field(1, description="Negative for reservation/sale; positive for restock")
    version: int | None = Field(None, description="Track central's version if known")
    operation_id: str = Field(str(uuid4()), description="Key of identification for table PendingChange")

class InventoryResponse(BaseModel):
    id: int
    sku: str
    name: str
    quantity: int
    version: int
    updated_at: datetime
    last_synced_at: datetime | None = None
    model_config = ConfigDict(from_attributes=True)

class GenericResponse(BaseModel):
    ok: bool
    message: str
