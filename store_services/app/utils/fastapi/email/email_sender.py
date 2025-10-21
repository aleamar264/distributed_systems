from pathlib import Path

from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class EmailConfig(BaseSettings):
	"""Email configuration for FastMail"""

	MAIL_USERNAME: str = Field(...)
	MAIL_PASSWORD: str = Field(...)
	MAIL_FROM: str = Field(...)
	MAIL_PORT: int = Field(...)
	MAIL_SERVER: str = Field(...)
	MAIL_STARTTLS: bool = Field(...)
	MAIL_SSL_TLS: bool = Field(...)
	USE_CREDENTIALS: bool = Field(...)
	VALIDATE_CERTS: bool = Field(...)

	model_config = SettingsConfigDict(
		env_file="other_env.env", env_file_encoding="utf-8"
	)


_env = EmailConfig()  # type: ignore
conf: ConnectionConfig = ConnectionConfig(
	**_env.model_dump(), TEMPLATE_FOLDER=Path(__file__).parent / "templates"
)

fm = FastMail(conf)
