import contextlib
from collections.abc import AsyncIterator
from typing import override

import logfire
from icecream import icecream
from logfire import instrument_sqlalchemy
from loguru import logger
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
	AsyncConnection,
	AsyncEngine,
	AsyncSession,
	async_sessionmaker,
	create_async_engine,
)

from utils.exceptions import ServiceError
from utils.fastapi.observability.logfire_settings import _env

from .general import AsyncDatabaseSessionManager, DefineGeneralDb


class AsyncDatabaseManager(AsyncDatabaseSessionManager):
	"""
	Class with following methods (all the methos are async):

	Methods:
		- async_close: Dispose the connection asynchronous
		- async_connect: Use the method ` allows the start point of the transaction to be stated explicitly,
		and allows that the transaction itself may be framed out as a context manager block so that the end
		of the transaction is instead implicit.`
		- async_session


	Args:
		AsyncDatabaseSessionManager (BaseSessionManager, ABC): Base class for Database managment
	"""

	def __init__(self, db_params: DefineGeneralDb, dev: str | None = None) -> None:
		"""
		Args:
			db_params (DefineGeneralDb): _description_
			dev (str | None): _description_
		"""
		super().__init__(db_params)
		url = self.create_url()
		icecream.ic(url)
		self.engine: AsyncEngine | None = create_async_engine(
			url, pool_size=50, max_overflow=0, pool_recycle=1800, pool_timeout=10
		)
		logfire.configure(
			service_name="user_services",
			token=_env.token,
			environment=_env.environment,
			send_to_logfire="if-token-present",
		)
		instrument_sqlalchemy(engine=self.engine)
		self._sessionmaker: async_sessionmaker[AsyncSession] = async_sessionmaker(
			autocommit=False, bind=self.engine
		)

	@override
	async def async_close(self) -> None:
		"""Close the connection to the db in async way

		Raises:
			ServiceError: Raise an error, if it's used in http send a 500
		"""
		if self.engine is None:
			raise ServiceError
		await self.engine.dispose()
		self.engine = None
		self._sessionmaker = None  # type: ignore

	@override
	@contextlib.asynccontextmanager
	async def async_connect(self) -> AsyncIterator[AsyncConnection]:
		"""_summary_

		Raises:
			ServiceError: Raise an error, if it's used in http send a 500

		Returns:
			AsyncIterator[AsyncConnection]: _description_

		Yields:
			Iterator[AsyncIterator[AsyncConnection]]: Yield the connection used with engine.begin
		"""
		if self.engine is None:
			raise ServiceError

		async with self.engine.begin() as connection:
			try:
				yield connection
			except SQLAlchemyError as SQLError:
				await connection.rollback()
				logger.error("Connection error ocurred")
				raise ServiceError from SQLError

	@override
	@contextlib.asynccontextmanager
	async def async_session(self) -> AsyncIterator[AsyncSession]:
		if not self._sessionmaker:
			logger.error("Sessionmaker is not available.")
			raise ServiceError

		session = self._sessionmaker()
		try:
			yield session
		except SQLAlchemyError as e:
			await session.rollback()
			logger.error(f"Session error could not be established {e}")
			raise ServiceError from e
		finally:
			await session.close()
