from datetime import UTC, datetime
from typing import Annotated

from sqlalchemy.dialects.sqlite import DATETIME, INTEGER, VARCHAR
from sqlalchemy.orm import Mapped, mapped_column

from core.db import MixInNameTable
from models import Base

primary_key = Annotated[int,mapped_column(INTEGER, primary_key=True)]


class ServiceCredentials(Base, MixInNameTable):
    id: Mapped[primary_key]
    service_name: Mapped[str] = mapped_column(VARCHAR, unique=True, nullable=False)
    service_secret: Mapped[str] = mapped_column(VARCHAR, nullable=False)
    role: Mapped[str] = mapped_column(VARCHAR, default="store")


class Inventory(Base, MixInNameTable):
    id: Mapped[primary_key]
    sku: Mapped[str] = mapped_column(VARCHAR(255), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    quantity: Mapped[int] = mapped_column(INTEGER, nullable=False, default=0)
    version: Mapped[int] = mapped_column(INTEGER, nullable=False, default=1)
    updated_at: Mapped[datetime] = mapped_column(DATETIME, nullable=False, default=datetime.now(UTC))