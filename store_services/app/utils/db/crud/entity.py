from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any, Literal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute


class GeneralCrudAsync[T](ABC):
	"""Class that define the factory to create a crud for any Entity

	Methods:
		- get_entity
		- get_entity_pagination
		- create_entity
		- update_entity
		- delete_entity
		- get_entity_by_id
		- get_entity_by_args
	"""

	def __init__(self, model: T) -> None:
		self.model = model

	@abstractmethod
	async def get_entity(self, db: AsyncSession, filter: tuple[Any]) -> Sequence[T]:
		pass

	@abstractmethod
	async def get_entity_pagination(
		self,
		db: AsyncSession,
		limit: int,
		offset: int,
		order_by: Literal["asc", "desc"],
		filter: tuple[Any],
	) -> tuple[Sequence[T], int]:
		pass

	@abstractmethod
	async def create_entity(self, entity_schema: Any, db: AsyncSession) -> T:
		pass

	@abstractmethod
	async def update_entity(
		self,
		entity_id: int | str,
		entity_schema: Any,
		db: AsyncSession,
		filter: tuple[Any],
	) -> T:
		pass

	@abstractmethod
	async def delete_entity(
		self, entity_id: int | str, db: AsyncSession, filter: tuple[Any]
	) -> None:
		pass

	@abstractmethod
	async def get_entity_by_id(self, entity_id: int | str, db: AsyncSession) -> T:
		pass

	@abstractmethod
	async def get_entity_by_args(
		self,
		column: InstrumentedAttribute[Any],
		entity_schema_value: Any,
		db: AsyncSession,
		filter: tuple[Any],
	) -> T | None:
		pass
