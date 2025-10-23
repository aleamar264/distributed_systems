from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from .config import get_settings

settings = get_settings()

engine = create_async_engine(url=settings.database_url,echo=False, future =True, connect_args={"check_same_thread": False})
session  = async_sessionmaker(bind=engine, expire_on_commit=False)


