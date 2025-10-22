from core.db import session as AsyncSessionLocal


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
