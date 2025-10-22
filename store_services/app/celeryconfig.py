"""Celery configuration for the store service.

This module is used by `celery --config=app.celeryconfig` when starting beat.
"""
from core.config import _env

# Broker URL (falls back to localhost RabbitMQ)
broker_url = _env.broker_url if hasattr(_env, "broker_url") else "amqp://guest:guest@rabbitmq:5672//"

# Beat schedule: run the store.process_pending_once task every 15 minutes
beat_schedule = {
    "process-pending-every-15m": {
        "task": "store.process_pending_once",
        "schedule": 15 * 60.0,
    },
}
