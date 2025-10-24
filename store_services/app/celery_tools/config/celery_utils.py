from celery import current_app as current_celery_app  # type: ignore
from celery.local import Proxy  # type: ignore
from celery.schedules import crontab
from .celery_config import settings


def create_celery() -> Proxy:
	# register_pydantic_model()
	celery_app = current_celery_app
	celery_app.config_from_object(settings, namespace="CELERY")
	celery_app.conf.update(task_track_started=True)
	celery_app.conf.update(worker_pool='solo')
	# celery_app.conf.update(task_serializer="pydantic")
	# celery_app.conf.update(result_serializer="pydantic")
	# celery_app.conf.update(event_serializer="pydantic")
	celery_app.conf.update(task_serializer="json")
	celery_app.conf.update(result_serializer="json")
	celery_app.conf.update(event_serializer="json")
	celery_app.conf.update(accept_content=["application/json"])
	celery_app.conf.update(result_accept_content=["application/json"])
	celery_app.conf.update(worker_concurrency=1)
	celery_app.conf.update(worker_max_tasks_per_child=100)
	celery_app.conf.update(worker_heartbeat=10)
	celery_app.conf.update(result_expires=200)
	celery_app.conf.update(result_persistent=True)
	celery_app.conf.update(enable_utc=True)
	celery_app.conf.update(worker_send_task_events=True)
	celery_app.conf.update(task_send_sent_event=True)
	celery_app.conf.update(worker_enable_remote_control=True)
	celery_app.conf.update(worker_prefetch_multiplier=2)
	celery_app.conf.update(task_acks_late=True)
	celery_app.conf.update(task_reject_on_worker_lost=True)
	celery_app.conf.update(broker_pool_limit=5)
	celery_app.conf.update(
		worker_log_format="[%(asctime)s: %(levelname)s/%(processName)s] %(message)s",
		worker_task_log_format="[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s",
	)
	celery_app.conf.update(
		beat_schedule={
			"process-pending-every-15m": {
				"task": "Store:process_pending_once_task",  # Use full path to task
				"schedule": crontab(minute="*/15"),  # Every 15 minutes
				"options": {
					"expires": 60 * 14,
					"queue": "Store"
				},  # Expire if not started within 14 minutes
			},
		}
	)
	return celery_app
