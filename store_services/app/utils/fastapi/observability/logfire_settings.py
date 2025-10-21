from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ReadEnvLogFireSettings(BaseSettings):
	"""
	Read Environment variables to get the basic configuration
	of the database. In this case the file used is a .env called
	`.database.env`

	If you want to use other file
	.. code-block:: python
	    ReadEnvDatabaseSettings(_env_file="name_of_env_file")

	"""  # noqa: E101

	token: str = Field(..., description="Token for LOGFIRE", alias="LOGFIRE_TOKEN")
	environment: str = Field("dev", description="", alias="LOGFIRE_ENV")
	model_config = SettingsConfigDict(
		env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore"
	)

_env = ReadEnvLogFireSettings()