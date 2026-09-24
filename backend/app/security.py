import os
import datetime
from typing import Optional, List
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from .database import get_db
from . import models

SECRET_KEY = os.getenv("DOCKIT_SECRET_KEY", "dev-only-change-in-real-deployment")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(models.User).filter(models.User.id == user_id, models.User.is_active == True).first()  # noqa: E712
    if user is None:
        raise credentials_exception
    return user


# ---------------------------------------------------------------------------
# Server-side permission matrix. This is the ONLY authorization authority —
# the frontend never decides who can do what; it only reflects what the
# backend allows, and every mutating endpoint below calls require_role()
# or require_action() explicitly. Hiding a button client-side is never
# treated as access control anywhere in this codebase.
# ---------------------------------------------------------------------------

ACTION_ROLES = {
    "case.create": {"investigating_officer", "admin"},
    "document.create": {"investigating_officer", "forensic_officer", "prosecutor", "admin"},
    "document.register": {"investigating_officer", "admin"},
    "document.submit_for_review": {"investigating_officer", "forensic_officer", "admin"},
    "document.approve": {"forensic_officer", "prosecutor", "court_clerk", "admin"},
    "document.reject": {"forensic_officer", "prosecutor", "court_clerk", "admin"},
    "document.new_version": {"investigating_officer", "forensic_officer", "prosecutor", "admin"},
    "document.transfer": {"investigating_officer", "forensic_officer", "prosecutor", "admin"},
    "document.acknowledge_receipt": {"forensic_officer", "prosecutor", "court_clerk", "admin"},
    "document.archive": {"admin", "court_clerk"},
    "evidence.create": {"investigating_officer", "forensic_officer", "admin"},
    "evidence.update_status": {"investigating_officer", "forensic_officer", "admin"},
    "adapter.trigger": {"investigating_officer", "prosecutor", "admin"},

    # --- Initiate & Collect ---
    "party.create": {"investigating_officer", "admin"},
    "note.create": {"investigating_officer", "forensic_officer", "prosecutor", "court_clerk", "admin"},

    # --- Manage & Review ---
    "task.create": {"investigating_officer", "prosecutor", "court_clerk", "admin"},
    "task.update": {"investigating_officer", "forensic_officer", "prosecutor", "court_clerk", "admin"},
    "comment.create": {"investigating_officer", "forensic_officer", "prosecutor", "court_clerk", "admin"},
    "case.assign_owner": {"investigating_officer", "admin"},

    # --- Deliver & Execute ---
    "notification.manage": {"investigating_officer", "forensic_officer", "prosecutor", "court_clerk", "admin"},

    # --- Store & Archive ---
    "case.set_retention": {"admin", "court_clerk"},
    "case.dispose": {"admin"},
    "case.set_active_status": {"admin", "court_clerk"},

    # --- Admin case-access control (per-case collaborators, restriction) ---
    "case.manage_collaborators": {"admin"},
    "case.set_restricted": {"admin"},

    # --- Admin content-blind approval gate on every document submission ---
    "admin_review.decide": {"admin"},

    # --- Disclosure to defence: zero access by default, Admin-only release ---
    "disclosure.request": {"prosecutor", "court_clerk"},
    "disclosure.decide": {"admin"},

    # --- Procedural / event-based classification ---
    "matter.create": {"investigating_officer", "forensic_officer", "prosecutor", "court_clerk", "admin"},
    "matter.assign": {"investigating_officer", "forensic_officer", "prosecutor", "court_clerk", "admin"},

    # --- Document content lock: owner (not Admin) approves who else can read it ---
    "document_access.request": {"investigating_officer", "forensic_officer", "prosecutor", "court_clerk"},
}


def require_action(action: str):
    def dependency(user: models.User = Depends(get_current_user)) -> models.User:
        allowed_roles = ACTION_ROLES.get(action)
        if allowed_roles is None:
            raise HTTPException(status_code=500, detail=f"Unknown action '{action}' — deny by default")
        if user.role.name not in allowed_roles and user.role.name != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role.name}' is not authorized to perform '{action}'",
            )
        return user
    return dependency


def check_case_access(db: Session, case: "models.Case", user: models.User) -> None:
    """Enforces case.is_restricted. A restricted case's content (documents,
    parties, notes, tasks, comments, evidence) is only visible to: the case
    creator, the case owner, users on the case's collaborator list, and
    Admin. Everyone else is blocked at the case boundary — being a valid
    role (e.g. some other Investigating Officer not on this case) is not
    enough once a case is marked restricted. Admin can still reach this
    point (so it can manage the case's flow/access), but the frontend's
    Admin view deliberately never renders document content."""
    if not getattr(case, "is_restricted", False):
        return
    if user.role.name == "admin":
        return
    if user.id in (case.created_by_id, case.owner_id):
        return
    is_collaborator = db.query(models.CaseCollaborator).filter(
        models.CaseCollaborator.case_id == case.id,
        models.CaseCollaborator.user_id == user.id,
    ).first()
    if is_collaborator:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="This case is restricted. You have not been granted access to it.",
    )


def _active_grant(db: Session, doc: "models.Document", user: models.User):
    """The single APPROVED, unrevoked, unexpired grant for this user on
    this document, if any. Expiry is checked here — server-side, on every
    call — not just displayed in the UI, so an expired grant can never be
    used to read or write content."""
    import datetime as _dt
    req = (
        db.query(models.DocumentAccessRequest)
        .filter(
            models.DocumentAccessRequest.document_id == doc.id,
            models.DocumentAccessRequest.requested_by_id == user.id,
            models.DocumentAccessRequest.status == "approved",
            models.DocumentAccessRequest.revoked_at.is_(None),
        )
        .order_by(models.DocumentAccessRequest.decided_at.desc())
        .first()
    )
    if not req:
        return None
    if req.expires_at and req.expires_at < _dt.datetime.utcnow():
        return None
    return req


def can_view_document_content(db: Session, doc: "models.Document", user: models.User) -> bool:
    """The content lock. Deliberately NOT the same rule as case access:
    being able to see a case, or even holding a document after a
    transfer, does not mean you can read it. Only the document's OWNER
    (its creator) can read it by default — everyone else, Admin
    included, needs an APPROVED, unexpired, unrevoked DocumentAccessRequest
    from that owner. Admin gets no bypass here: content visibility is the
    owner's call, not Admin's, by explicit design."""
    if user.id == doc.created_by_id:
        return True
    return _active_grant(db, doc, user) is not None


def can_edit_document_content(db: Session, doc: "models.Document", user: models.User) -> bool:
    """True only if the owner, or an active grant in 'edit' mode."""
    if user.id == doc.created_by_id:
        return True
    grant = _active_grant(db, doc, user)
    return grant is not None and grant.granted_mode == "edit"


def can_append_document_content(db: Session, doc: "models.Document", user: models.User) -> bool:
    """True if the owner, or an active grant in 'edit' or 'append' mode."""
    if user.id == doc.created_by_id:
        return True
    grant = _active_grant(db, doc, user)
    return grant is not None and grant.granted_mode in ("edit", "append")
