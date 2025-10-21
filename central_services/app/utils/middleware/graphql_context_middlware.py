from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class AddGraphQLContextMiddleware(BaseHTTPMiddleware):
	async def dispatch(
		self, request: Request, call_next: Callable[[Request], Awaitable[Any]]
	) -> Any:
		if request.url.path == "/graphql":
			# Extract query and variables
			body = await request.json()
			request.state.context = {
				"query": body.get("query"),
				"variables": body.get("variables", {}),
			}
		response = await call_next(request)
		cache_source = getattr(request.state, "context", {}).get("cache_source")
		if cache_source:
			response.headers["X-Cache-Source"] = cache_source
			if cache_source == "cache":
				response.headers["Cache-Control"] = "max-age=3600"
		return response
