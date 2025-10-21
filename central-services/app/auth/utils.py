from datetime import UTC, datetime, timedelta
from typing import TypedDict

import jwt
from config import _env


class Token(TypedDict):
    sub: str
    role: str


def create_access_token(data: Token)->str:
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(_env.jwt_expiration)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, _env.jwt_secrets, algorithm=_env.jwt_algorithm)
