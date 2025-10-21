from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

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