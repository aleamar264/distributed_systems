import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt import PyJWTError

from core.config import get_settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
settings = get_settings()

def get_current_services(token: str = Depends(oauth2_scheme)):
	try:
		payload = jwt.decode(token, settings.jwt_secrets, algorithms=[settings.jwt_algorithm])
		return payload.get("sub")
	except PyJWTError as err:
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail="Invalid token",
			headers={"WWW-Authenticate": "Bearer"},
		) from err
