from app.celery_app import celery_app
from app.services.prediction_service import execute_prediction_job


@celery_app.task(name="mlservice.run_prediction_task")
def run_prediction_task(job_id: int) -> None:
    execute_prediction_job(job_id)
