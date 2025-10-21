from fastapi import Request
from opentelemetry.trace import Span


def server_request_hook(span: Span, scope: dict):
	"""
	Hook to customize span attributes and naming.
	This function is used to send data of telemetry to Jaeger
	using pydantic logfire
	"""
	if not span.is_recording():
		return

	# Extract request from ASGI scope
	request = Request(scope)
	method = request.method
	route = scope.get("route")
	route_path = route.path if route else request.url.path

	# Set better span name
	span.update_name(f"{method} {route_path}")

	# Semantic attributes
	span.set_attribute("http.method", method)
	span.set_attribute("http.route", route_path)
	span.set_attribute("http.target", request.url.path)
	span.set_attribute("http.scheme", request.url.scheme)
	span.set_attribute("http.host", request.url.hostname)

	# Optional: function and module
	endpoint = scope.get("endpoint")
	if endpoint:
		span.set_attribute("code.function", endpoint.__name__)
		span.set_attribute("code.namespace", endpoint.__module__)
