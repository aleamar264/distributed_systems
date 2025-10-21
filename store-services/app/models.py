from datetime import datetime
from typing import Annotated
from uuid import UUID

from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Uuid
from sqlalchemy.dialects.sqlite import DATETIME, FLOAT, INTEGER, VARCHAR
from sqlalchemy.orm import Mapped, mapped_column
from utils.db.general import MixInNameTable

from base import Base
from status import Status

primary_key = Annotated[int,mapped_column(INTEGER(), primary_key=True, index=True, unique=True)]

class Products(Base, MixInNameTable):
    id: Mapped[primary_key]
    sku: Mapped[str] = mapped_column(VARCHAR(255), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(VARCHAR(255), unique=True, nullable=False)
    price: Mapped[float] = mapped_column(FLOAT(), nullable=False, unique=False, index=True)

class Inventory(Base, MixInNameTable):
    id: Mapped[primary_key]
    sku: Mapped[str] = mapped_column(VARCHAR(255), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    quantity: Mapped[int] = mapped_column(INTEGER, nullable=False, default=0)
    version: Mapped[int] = mapped_column(INTEGER, nullable=False, default=1)
    updated_at: Mapped[datetime] = mapped_column(DATETIME, nullable=False)
    last_synced_at: Mapped[datetime] = mapped_column(DATETIME)