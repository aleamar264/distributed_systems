import os
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from .async_database_manager import AsyncDatabaseManager
from .general import DefineGeneralDb, ReadEnvDatabaseSettings

# import logfire


_env = ReadEnvDatabaseSettings(_env_file=".env" if os.path.exists(".env") else None)  # type: ignore
_database: DefineGeneralDb = DefineGeneralDb(**_env.model_dump())
sessionmanager = AsyncDatabaseManager(_database)


async def get_db_session() -> AsyncIterator[AsyncSession]:
	async with sessionmanager.async_session() as session:
		yield session


depend_db_annotated = Annotated[AsyncSession, Depends(get_db_session)]
