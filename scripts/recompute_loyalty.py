from app.db.session import SessionLocal
from app.services.loyalty_service import recompute_all_users_loyalty


def main() -> None:
    db = SessionLocal()
    try:
        recompute_all_users_loyalty(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
