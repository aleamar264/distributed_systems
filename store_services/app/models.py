from datetime import UTC, datetime
from enum import Enum
from typing import Annotated
from uuid import UUID, uuid4

from sqlalchemy import Enum as SQLEnum, Text
from sqlalchemy import ForeignKey, Uuid
from sqlalchemy.dialects.sqlite import DATETIME, FLOAT, INTEGER, VARCHAR
from sqlalchemy.orm import Mapped, mapped_column
from utils.db.general import MixInNameTable

from base import Base
from status import Status

primary_key = Annotated[int, mapped_column(INTEGER(), primary_key=True, index=True, unique=True)]


class SyncStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class Products(Base, MixInNameTable):
    id: Mapped[primary_key]
    sku: Mapped[str] = mapped_column(VARCHAR(255), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(VARCHAR(255), unique=True, nullable=False)
    price: Mapped[float] = mapped_column(FLOAT(), nullable=False, unique=False, index=True)


class Inventory(Base, MixInNameTable):
    """Local inventory state."""
    id: Mapped[primary_key]
    sku: Mapped[str] = mapped_column(VARCHAR(255), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    quantity: Mapped[int] = mapped_column(INTEGER, nullable=False, default=0)
    version: Mapped[int] = mapped_column(INTEGER, nullable=False, default=1)
    updated_at: Mapped[datetime] = mapped_column(
        DATETIME, nullable=False, default=lambda: datetime.now(UTC)
    )
    last_synced_at: Mapped[datetime] = mapped_column(
        DATETIME, nullable=True
    )


class PendingChange(Base, MixInNameTable):
    """Track changes that need to be synced to central."""
    id: Mapped[primary_key]
    operation_id: Mapped[str] = mapped_column(
        VARCHAR(255), unique=True, nullable=False, default=lambda: str(uuid4())
    )
    inventory_id: Mapped[int] = mapped_column(ForeignKey("inventory.id"))
    sku: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    delta: Mapped[int] = mapped_column(INTEGER, nullable=False)
    local_version: Mapped[int] = mapped_column(INTEGER, nullable=False)
    central_version: Mapped[int] = mapped_column(INTEGER, nullable=True)
    status: Mapped[str] = mapped_column(
        SQLEnum(SyncStatus), nullable=False, default=SyncStatus.PENDING
    )
    error: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DATETIME, nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DATETIME, nullable=False, default=lambda: datetime.now(UTC)
    )