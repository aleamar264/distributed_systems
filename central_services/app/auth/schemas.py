from pydantic import BaseModel, Field


class TokenRequest(BaseModel):
    service_name: str
    service_secret: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = Field("bearer", description="Type of authentication")