from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from .. import models, schemas, security
from ..database import get_db

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=List[schemas.UserOut])
def list_users(db: Session = Depends(get_db), user: models.User = Depends(security.get_current_user)):
    """Active users only, for owner/assignee pickers in the frontend.
    Any authenticated user can list colleagues by design — this is
    directory information, not something requiring elevated permission."""
    users = db.query(models.User).filter(models.User.is_active == True).all()  # noqa: E712
    return [
        schemas.UserOut(id=u.id, username=u.username, full_name=u.full_name,
                         role=u.role.name, department=u.department)
        for u in users
    ]
