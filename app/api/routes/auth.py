from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.auth import Token, UserLogin, UserRegister
from app.schemas.user import UserOut
from app.services import auth_service
from app.services.loyalty_service import loyalty_status_for_user

router = APIRouter()


@router.post("/register", response_model=UserOut)
def register_user(user: UserRegister, db: Session = Depends(get_db)):
    u = auth_service.register_user(db, user.email, user.password)
    return UserOut(
        id=u.id,
        email=u.email,
        role=u.role,
        is_active=u.is_active,
        created_at=u.created_at,
        loyalty=loyalty_status_for_user(db, u.id),
    )


@router.post("/login", response_model=Token)
def login_user(user: UserLogin, db: Session = Depends(get_db)):
    return auth_service.login_user(db, user.email, user.password)
