import os
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class ReadEnvSettings(BaseSettings):
    """
    Read Environment variables to get the basic configuration
    of the database. In this case the file used is a .env called
    `.database.env`

    If you want to use other file
    .. code-block:: python
        ReadEnvDatabaseSettings(_env_file="name_of_env_file")

    """  # noqa: E101

    jwt_secrets: str = Field(..., description="Secret used for the JWT config", alias="JWT_SECRET")
    jwt_algorithm: str = Field("HS256", description="Algorith used in the JWT Auth", alias="JWT_ALGORITHM")
    database_url: str = Field(default="sqlite+aiosqlite:///./central_inventory.db", description="url or path for the sqlite db", alias="DATABASE_URL")
    jwt_expiration: int = Field(15, description="Minutes to expire the JWT token", alias="JWT_EXPIRATION")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")



@lru_cache
def get_settings()-> ReadEnvSettings:
    return  ReadEnvSettings(_env_file=".env" if os.path.exists(".env") else None)
