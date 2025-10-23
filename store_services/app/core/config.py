from functools import lru_cache
import os

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class ReadEnvSettings(BaseSettings):
    """
    Read Environment variables to get the basic configuration
    of the database. In this case the file used is a .env called
    `.database.env`

    If you want to use other file
    .. code-block:: python
        ReadEnvDatabaseSettings(_env_file="name_of_env_file")

    """  # noqa: E101
    central_url: HttpUrl = Field("http://central-service:8000", description="URL for the central services", alias="CENTRAL_URL")
    service_name: str = Field("store-1", description="Name of the services (this is unique)", alias="SERVICE_NAME")
    services_secret: str = Field(..., description="Secret used for the services", alias="SERVICE_SECRET")
    jwt_secrets: str = Field(..., description="Secret used for the JWT config", alias="JWT_SECRET")
    jwt_algorithm: str = Field("HS256", description="Algorith used in the JWT Auth", alias="JWT_ALGORITHM")
    database_url: str = Field(..., description="url or path for the sqlite db", alias="DATABASE_URL")
    broker_url: str = Field(..., description="RabbitMQ host", alias="RABBITMQ_URL")
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")



@lru_cache
def get_settings()->ReadEnvSettings:
    return ReadEnvSettings(_env_file=".env" if os.path.exists(".env") else None)

