class GeneralErrorAPI(Exception):
	def __init__(
		self, message: str = "Service is unavailable", name: str = "API"
	) -> None:
		self.message = message
		self.name = name
		super().__init__(self.message, self.name)


class ServiceError(GeneralErrorAPI):
	"""Failed to connect to the service."""

	pass
