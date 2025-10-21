import re
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Coroutine
from contextlib import asynccontextmanager
from typing import Any

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession
from sqlalchemy.orm import declared_attr


class ReadEnvDatabaseSettings(BaseSettings):
	"""
	Read Environment variables to get the basic configuration
	of the database. In this case the file used is a .env called
	`.database.env`

	If you want to use other file
	.. code-block:: python
	    ReadEnvDatabaseSettings(_env_file="name_of_env_file")

	"""  # noqa: E101

	drivername: str = Field("postgresql+asyncpg", description="Database Driver")
	username: str = Field(..., description="Database Username")
	password: str = Field(..., description="Database Password")
	host: str = Field(..., description="Database Host")
	database: str = Field(..., description="Database Name")
	port: int = Field(..., description="Database Port")

	model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


class DefineGeneralDb(BaseModel):
	"""
	Use the parameters got from ReadEnvDatabaseSettings to define the variables
	needed to create the Session.
	"""

	drivername: str = Field(
		"postgresql+asyncpg",
		description="Database Driver",
		examples=["mysql+pymysql", "postgresql+psycopg2", "postgresql+asyncpg"],
	)
	username: str = Field(..., description="Database Username")
	password: str = Field(..., description="Database Password")
	host: str = Field(..., description="Database Host")
	database: str = Field(..., description="Database Name")
	port: int = Field(..., description="Database Port")


class BaseSessionManager:
	"""Base Class that handle the parameters of the database and
	create the url using the tool of SQLAlchemy"""

	def __init__(self, db_params: DefineGeneralDb) -> None:
		self.db_params = db_params

	def create_url(self) -> URL:
		"""Create URL driver connection for SQLAlchmey, create
		sync and async urls. The sync connction is for use of the
		sqlalchemy-utils create databases (Schemas) in MySQL, the async
		url is for all the operations in the db.

		Also this function call the .local.env to know if the environment is local.

		.. code-block:: env
			dev=true

		Returns:
			URL: Async Url
		"""
		return URL.create(
			database=self.db_params.database,
			username=self.db_params.username,
			drivername=self.db_params.drivername,
			host=self.db_params.host,
			password=self.db_params.password,
			port=self.db_params.port,
		)


class AsyncDatabaseSessionManager(BaseSessionManager, ABC):
	"""Abstrac class for async connection to the database"""

	@abstractmethod
	def async_close(self) -> Coroutine[Any, Any, None]: ...

	@abstractmethod
	@asynccontextmanager
	def async_connect(self) -> AsyncIterator[AsyncConnection]: ...

	@abstractmethod
	@asynccontextmanager
	def async_session(self) -> AsyncIterator[AsyncSession]: ...


class MixInNameTable:
	"""Class that take the class name and lower this to create the table name

	Returns:
		str: name in lowercase
	"""

	@declared_attr.directive
	def __tablename__(cls) -> str:
		name = re.sub(r"(?<!^)(?=[A-Z])", "_", cls.__name__).lower()  # type: ignore
		return name
