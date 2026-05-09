from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.services.loyalty_service import ensure_loyalty_tiers_seeded


def seed_loyalty_tiers() -> None:
    db: Session = SessionLocal()
    try:
        ensure_loyalty_tiers_seeded(db)
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    seed_loyalty_tiers()
