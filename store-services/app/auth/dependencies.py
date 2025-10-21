import jwt
from config import _env
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt import PyJWTError

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def get_current_services(token: str = Depends(oauth2_scheme)):
	try:
		payload = jwt.decode(token, _env.jwt_secrets, algorithms=[_env.jwt_algorithm])
		return payload.get("sub")
	except PyJWTError as err:
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail="Invalid token",
			headers={"WWW-Authenticate": "Bearer"},
		) from err
