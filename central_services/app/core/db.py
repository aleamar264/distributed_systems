from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from .config import _env




engine = create_async_engine(url=_env.database_url,echo=False, future =True, connect_args={"check_same_thread": False})
session  = async_sessionmaker(bind=engine, expire_on_commit=False)


