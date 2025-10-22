from datetime import UTC, datetime
from typing import Annotated

from sqlalchemy.dialects.sqlite import DATETIME, INTEGER, VARCHAR
from sqlalchemy.orm import Mapped, mapped_column

from .base import MixInNameTable, ModelBase

primary_key = Annotated[int, mapped_column(INTEGER, primary_key=True)]


class ServiceCredentials(ModelBase, MixInNameTable):
    id: Mapped[primary_key]
    service_name: Mapped[str] = mapped_column(VARCHAR, unique=True, nullable=False)
    service_secret: Mapped[str] = mapped_column(VARCHAR, nullable=False)
    role: Mapped[str] = mapped_column(VARCHAR, default="store")


class Inventory(ModelBase, MixInNameTable):
    id: Mapped[primary_key]
    sku: Mapped[str] = mapped_column(VARCHAR(255), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    quantity: Mapped[int] = mapped_column(INTEGER, nullable=False, default=0)
    version: Mapped[int] = mapped_column(INTEGER, nullable=False, default=1)
    updated_at: Mapped[datetime] = mapped_column(DATETIME, nullable=False, default=lambda: datetime.now(UTC))


class IdempotencyKey(ModelBase, MixInNameTable):
    """Tracks idempotency keys to prevent duplicate processing of retries.

    For prototype we store a short-lived record of the request and response.
    """
    id: Mapped[primary_key]
    key: Mapped[str] = mapped_column(VARCHAR(255), unique=True, nullable=False)
    service_name: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    request_hash: Mapped[str] = mapped_column(VARCHAR(255), nullable=True)
    response_body: Mapped[str] = mapped_column(VARCHAR, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DATETIME, nullable=False, default=lambda: datetime.now(UTC))
    expires_at: Mapped[datetime] = mapped_column(DATETIME, nullable=True)
