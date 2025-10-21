import hashlib
import json
from collections.abc import Callable
from typing import Annotated, Any

from fastapi import Depends
from graphql import parse, print_ast
from redis.asyncio import Redis
from strawberry import Info

from utils.dependencies.redis_cache import get_master, get_replica


def normalize_query(query: str) -> str:
	"""
	Normalize a GraphQL query by parsing and re-serializing it to remove unnecessary differences.
	"""
	parsed_query = parse(query)
	return print_ast(parsed_query)


def generate_cache_key(query: str, variables: dict[str, Any]) -> str:
	"""
	Generate a unique key based from query normalize/variables
	"""
	normalized_query = normalize_query(query)
	key_data = {"query": normalized_query, "variables": variables}
	return hashlib.sha256(json.dumps(key_data, sort_keys=True).encode()).hexdigest()


def tag_cache_key(key: str, tag: str, redis_master: Redis) -> None:
	"""
	Associate a cache key with tags for invalidation (mutations)
	"""
	redis_master.sadd(f"tag:{tag}", key)


async def invalidate_tag(
	tags: list[str], redis_master: Redis, redis_replica: Redis
) -> None:
	for tag in tags:
		keys = await redis_replica.smembers(f"tag:{tag}")  # type: ignore # this is ignored 'cause the response can be an Awaitable or not
		for key in keys:
			redis_master.delete(key)
		redis_master.delete(f"tag:{tag}")


def cache_resolver(
	redis_client: Annotated[Redis, Depends(get_replica)],
	redis_master: Annotated[Redis, Depends(get_master)],
	tag: str,
	ttl: int = 3600,
) -> Callable[..., Any]:
	def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
		async def wrapper(*args: tuple[Any, Any], **kwargs: dict[str, Any]) -> Any:
			info: Info[Any, Any] = kwargs.get("info")  #  type: ignore
			query = info.context["query"]
			variables = info.context.get("variables", {})

			cache_key = generate_cache_key(query, variables)
			cached_response = await redis_client.get(cache_key)
			if cached_response:
				info.context["cache_source"] = "cache"
				return json.loads(cached_response)
			result = await func(*args, **kwargs)
			await redis_master.setex(cache_key, ttl, json.dumps(result))
			tag_cache_key(cache_key, tag, redis_master)
			info.context["cache_source"] = "database"
			return result

		return wrapper

	return decorator
