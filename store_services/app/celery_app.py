from celery import Celery
from core.config import _env

# Broker URL from env (default to amqp://guest:guest@rabbitmq:5672//)
broker = _env.broker_url if hasattr(_env, 'broker_url') else 'amqp://guest:guest@localhost:5672//'

celery_app = Celery('store_sync', broker=broker)

# Configure a beat schedule: run the `store.process_pending_once` task every 15 minutes
celery_app.conf.beat_schedule = {
	'process-pending-every-15m': {
		'task': 'store.process_pending_once',
		'schedule': 15 * 60.0,
	},
}

# Note: Some deployments prefer to run a separate `celery-beat` container to avoid race conditions.
