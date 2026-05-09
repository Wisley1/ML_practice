import logging

from app.celery_app import celery_app
from app.db.session import SessionLocal
from app.services.loyalty_service import recompute_all_users_loyalty

logger = logging.getLogger(__name__)


@celery_app.task(name="mlservice.recompute_loyalty_task")
def recompute_loyalty_task() -> None:
    db = SessionLocal()
    try:
        recompute_all_users_loyalty(db)
    except Exception:
        db.rollback()
        logger.exception("recompute_loyalty_task failed")
        raise
    finally:
        db.close()
