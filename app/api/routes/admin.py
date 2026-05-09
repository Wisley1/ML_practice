from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_admin
from app.models.user import User
from app.schemas.admin import AdminUserRow
from app.services.admin_service import list_users_for_admin

router = APIRouter()


@router.get("/users", response_model=list[AdminUserRow])
def admin_list_users(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return list_users_for_admin(db)
