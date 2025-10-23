from pydantic import UUID4, BaseModel, Field


class Products(BaseModel):
    id: int
    sku: str
    name: str
    price: int

class UpdateInventory(BaseModel):
    sku: str
    delta: int = Field(..., description="Negative for reservation/sale; positive for restock")
    version: int
    operation_id: str

class GenericResponse(BaseModel):
    ok: bool
    message: str
