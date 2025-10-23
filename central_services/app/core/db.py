from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession

from .config import get_settings

settings = get_settings()

engine = create_async_engine(url=settings.database_url,echo=False, future =True)
session  = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)


