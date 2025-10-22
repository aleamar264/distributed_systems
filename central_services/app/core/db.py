import asyncio
import re

from config import _env
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, declared_attr

from models import Base  # SQLAlchemy declarative base that will hold metadata


class Base(DeclarativeBase):
    pass


engine = create_async_engine(url=_env.database_url,echo=False, future =True, connect_args={"check_same_thread": False})
session  = async_sessionmaker(bind=engine, expire_on_commit=False)


class MixInNameTable:
	"""Class that take the class name and lower this to create the table name

	Returns:
		str: name in lowercase
	"""

	@declared_attr.directive
	def __tablename__(cls) -> str:
		name = re.sub(r"(?<!^)(?=[A-Z])", "_", cls.__name__).lower()  # type: ignore
		return name


async def init_db(echo: bool | None = False) -> None:
	"""Create database tables from SQLAlchemy models. For prototype only."""
	# For sqlite async, use engine.begin() and run sync create_all in executor
	async with engine.begin() as conn:
		# For sqlite, synchronous create_all must be run via run_sync
		try:
			await conn.run_sync(Base.metadata.create_all)
		except Exception as err:
			print("Already created databases")