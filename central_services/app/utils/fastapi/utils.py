from itsdangerous import BadTimeSignature, SignatureExpired, URLSafeTimedSerializer

from exception.handler_exception import InvalidTokenError

token = URLSafeTimedSerializer(
	secret_key="", salt="Email_Verification_&_Forgot_password"
)


def url_with_token(message: dict[str, str]) -> str:
	return token.dumps(message)


def verify_token(token_to_verify: str) -> str:
	try:
		message: dict[str, str] = token.loads(token_to_verify, max_age=1800)
		id: str = message["id"]
	except SignatureExpired as err:
		raise InvalidTokenError(
			"Time expired for the token, max time is 1 hour"
		) from err
	except BadTimeSignature as err:
		raise InvalidTokenError(
			"Different signature, please ask for other link"
		) from err
	return id
