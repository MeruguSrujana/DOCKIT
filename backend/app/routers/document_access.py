from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import datetime

from .. import models, schemas, security
from ..database import get_db
from ..events import log_event, notify

router = APIRouter(prefix="/document-access", tags=["document-access"])

VALID_MODES = ("view", "edit", "append")


def _is_expired(r: models.DocumentAccessRequest) -> bool:
    if r.status != "approved" or r.revoked_at:
        return False
    return bool(r.expires_at and r.expires_at < datetime.datetime.utcnow())


def _to_out(r: models.DocumentAccessRequest) -> schemas.DocumentAccessRequestOut:
    return schemas.DocumentAccessRequestOut(
        id=r.id, document_id=r.document_id, doc_ref=r.document.doc_ref, doc_type=r.document.doc_type,
        case_id=r.case_id, requested_by_id=r.requested_by_id, requested_by_name=r.requested_by.full_name,
        owner_id=r.owner_id, owner_name=r.owner.full_name, reason=r.reason,
        requested_mode=r.requested_mode, status=r.status,
        decision_reason=r.decision_reason,
        granted_mode=r.granted_mode, granted_days=r.granted_days,
        granted_at=r.granted_at, expires_at=r.expires_at, revoked_at=r.revoked_at,
        is_expired=_is_expired(r),
        created_at=r.created_at, decided_at=r.decided_at,
    )


@router.post("", response_model=schemas.DocumentAccessRequestOut)
def raise_request(
    payload: schemas.DocumentAccessRequestCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(security.require_action("document_access.request")),
):
    doc = db.query(models.Document).filter(models.Document.id == payload.document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    case = db.query(models.Case).filter(models.Case.id == doc.case_id).first()
    security.check_case_access(db, case, user)

    if user.id == doc.created_by_id:
        raise HTTPException(status_code=400, detail="You already own this document — it isn't locked for you")

    if payload.requested_mode not in VALID_MODES:
        raise HTTPException(status_code=400, detail=f"requested_mode must be one of {VALID_MODES}")

    existing_pending = db.query(models.DocumentAccessRequest).filter(
        models.DocumentAccessRequest.document_id == doc.id,
        models.DocumentAccessRequest.requested_by_id == user.id,
        models.DocumentAccessRequest.status == "pending",
    ).first()
    if existing_pending:
        raise HTTPException(status_code=400, detail="You already have a pending request for this document")

    req = models.DocumentAccessRequest(
        document_id=doc.id, case_id=doc.case_id,
        requested_by_id=user.id, owner_id=doc.created_by_id, reason=payload.reason,
        requested_mode=payload.requested_mode,
    )
    db.add(req)
    db.flush()

    log_event(db, case_id=doc.case_id, document_id=doc.id, actor_id=user.id,
              event_type="access_requested",
              details=f"{user.full_name} requested access to {doc.doc_ref}")

    notify(db, user_id=doc.created_by_id, notif_type="document_access_requested",
           message=f"{user.full_name} is requesting {payload.requested_mode.upper()} access to {doc.doc_ref} ({doc.doc_type.replace('_', ' ')}) — you own this document",
           case_id=doc.case_id, document_id=doc.id)

    db.commit()
    db.refresh(req)
    return _to_out(req)


@router.get("/document/{document_id}", response_model=List[schemas.DocumentAccessRequestOut])
def list_requests_for_document(
    document_id: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(security.get_current_user),
):
    """The owner sees every request on their document; anyone else only
    sees their own — so a requester can check their own request's status
    without seeing who else has asked."""
    doc = db.query(models.Document).filter(models.Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    q = db.query(models.DocumentAccessRequest).filter(models.DocumentAccessRequest.document_id == document_id)
    if user.id != doc.created_by_id:
        q = q.filter(models.DocumentAccessRequest.requested_by_id == user.id)

    rows = q.order_by(models.DocumentAccessRequest.created_at.desc()).all()
    return [_to_out(r) for r in rows]


@router.get("/mine/pending", response_model=List[schemas.DocumentAccessRequestOut])
def list_my_pending_owner_requests(
    db: Session = Depends(get_db),
    user: models.User = Depends(security.get_current_user),
):
    """Pending requests waiting on documents *I* own — across every case
    I have documents in. This is the owner's approval queue."""
    rows = db.query(models.DocumentAccessRequest).filter(
        models.DocumentAccessRequest.owner_id == user.id,
        models.DocumentAccessRequest.status == "pending",
    ).order_by(models.DocumentAccessRequest.created_at.desc()).all()
    return [_to_out(r) for r in rows]


@router.post("/{request_id}/decide", response_model=schemas.DocumentAccessRequestOut)
def decide_request(
    request_id: str,
    payload: schemas.AccessDecision,
    db: Session = Depends(get_db),
    user: models.User = Depends(security.get_current_user),
):
    """Only the document's OWNER may decide — not Admin, not any role
    generically. This is checked directly against ownership, not the
    role permission matrix, because the whole point is that content
    access is the owner's call."""
    req = db.query(models.DocumentAccessRequest).filter(models.DocumentAccessRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    if user.id != req.owner_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the person who uploaded this document can approve or reject access to it",
        )

    if payload.status not in ("approved", "rejected"):
        raise HTTPException(status_code=400, detail="status must be approved or rejected")

    req.status = payload.status
    req.decision_reason = payload.reason
    req.decided_at = datetime.datetime.utcnow()

    detail = f"Access to {req.document.doc_ref} {payload.status} by owner {user.full_name}"

    if payload.status == "approved":
        mode = payload.granted_mode or req.requested_mode
        if mode not in VALID_MODES:
            raise HTTPException(status_code=400, detail=f"granted_mode must be one of {VALID_MODES}")
        days = payload.granted_days
        if not days or days < 1:
            raise HTTPException(status_code=400, detail="granted_days is required when approving and must be at least 1")
        req.granted_mode = mode
        req.granted_days = days
        req.granted_at = req.decided_at
        req.expires_at = req.decided_at + datetime.timedelta(days=days)
        detail += f" — {mode.upper()} access for {days} day(s), expires {req.expires_at.isoformat()}"

    log_event(db, case_id=req.case_id, document_id=req.document_id, actor_id=user.id,
              event_type="access_decided", details=detail)

    grant_note = ""
    if payload.status == "approved":
        grant_note = f" — {req.granted_mode.upper()} mode, {req.granted_days} day(s)"
    notify(db, user_id=req.requested_by_id, notif_type="document_access_decided",
           message=f"Your request for {req.document.doc_ref} was {payload.status} by {user.full_name}{grant_note}",
           case_id=req.case_id, document_id=req.document_id)

    db.commit()
    db.refresh(req)
    return _to_out(req)


@router.post("/{request_id}/revoke", response_model=schemas.DocumentAccessRequestOut)
def revoke_access(
    request_id: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(security.get_current_user),
):
    """Only the owner can revoke a grant early, before its expiry."""
    req = db.query(models.DocumentAccessRequest).filter(models.DocumentAccessRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if user.id != req.owner_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the person who uploaded this document can revoke access")
    if req.status != "approved" or req.revoked_at:
        raise HTTPException(status_code=400, detail="This request is not an active grant")

    req.revoked_at = datetime.datetime.utcnow()

    log_event(db, case_id=req.case_id, document_id=req.document_id, actor_id=user.id,
              event_type="access_revoked",
              details=f"Access to {req.document.doc_ref} revoked early by owner {user.full_name}")

    notify(db, user_id=req.requested_by_id, notif_type="document_access_revoked",
           message=f"Your access to {req.document.doc_ref} was revoked by {user.full_name}",
           case_id=req.case_id, document_id=req.document_id)

    db.commit()
    db.refresh(req)
    return _to_out(req)


@router.get("/document/{document_id}/authorized-officers", response_model=List[schemas.AuthorizedOfficerOut])
def list_authorized_officers(
    document_id: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(security.get_current_user),
):
    """Owner-only: every officer who has ever been granted access to this
    document, with their current status (active / expired / revoked)."""
    doc = db.query(models.Document).filter(models.Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if user.id != doc.created_by_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the person who uploaded this document can view this")

    rows = db.query(models.DocumentAccessRequest).filter(
        models.DocumentAccessRequest.document_id == document_id,
        models.DocumentAccessRequest.status == "approved",
    ).order_by(models.DocumentAccessRequest.granted_at.desc()).all()

    out = []
    for r in rows:
        if r.revoked_at:
            row_status = "revoked"
        elif _is_expired(r):
            row_status = "expired"
        else:
            row_status = "active"
        out.append(schemas.AuthorizedOfficerOut(
            request_id=r.id, user_id=r.requested_by_id, user_name=r.requested_by.full_name,
            role=r.requested_by.role.label if r.requested_by.role else "", mode=r.granted_mode or "",
            granted_at=r.granted_at, expires_at=r.expires_at, status=row_status,
        ))
    return out
