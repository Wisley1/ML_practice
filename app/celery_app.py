from celery import Celery
from celery.schedules import crontab

from core.config import settings

celery_app = Celery(
    "mlservice",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.timezone = "UTC"
celery_app.conf.beat_schedule = {
    "recompute-loyalty-monthly": {
        "task": "mlservice.recompute_loyalty_task",
        "schedule": crontab(day_of_month=1, hour=0, minute=0),
    },
}

import app.tasks.loyalty_tasks  # noqa: E402,F401
import app.tasks.prediction_tasks  # noqa: E402,F401
