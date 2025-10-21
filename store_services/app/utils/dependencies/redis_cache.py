from redis.asyncio import Redis

redis_master = Redis(
	host="redis-master.redis.svc.cluster.local",
	port=6379,
	decode_responses=True,
	password="test-redis",
)
redis_replica = Redis(
	host="redis-replicas.redis.svc.cluster.local",
	port=6379,
	decode_responses=True,
	password="test-redis",
)


async def get_master() -> Redis:
	return redis_master


async def get_replica() -> Redis:
	return redis_replica
