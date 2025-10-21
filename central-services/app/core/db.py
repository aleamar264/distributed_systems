import re

from config import _env
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, declared_attr


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
