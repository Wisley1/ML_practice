

@celery_app.task
def run_prediction_task(user_id: int, model_id: int, input_text: str):
    return run_prediction(user_id, model_id, input_text)