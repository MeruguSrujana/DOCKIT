from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import datetime

from .. import models, schemas, security
from ..database import get_db
from ..events import log_event

router = APIRouter(prefix="/admin-reviews", tags=["admin-reviews"])


def _to_out(r: models.AdminReview) -> schemas.AdminReviewOut:
    return schemas.AdminReviewOut(
        id=r.id, case_id=r.case_id, case_number=r.case.case_number,
        document_id=r.document_id, doc_type=r.doc_type,
        submitted_by_name=r.submitted_by.full_name, status=r.status,
        decision_reason=r.decision_reason, created_at=r.created_at, decided_at=r.decided_at,
    )


@router.get("", response_model=List[schemas.AdminReviewOut])
def list_admin_reviews(
    status_filter: str = "pending",
    db: Session = Depends(get_db),
    user: models.User = Depends(security.require_action("admin_review.decide")),
):
    """Admin-only, metadata-only queue. The response schema has no
    content/title field by design — Admin approves the fact that a
    submission happened, not what it says."""
    q = db.query(models.AdminReview)
    if status_filter and status_filter != "all":
        q = q.filter(models.AdminReview.status == status_filter)
    rows = q.order_by(models.AdminReview.created_at.desc()).all()
    return [_to_out(r) for r in rows]


@router.post("/{review_id}/decide", response_model=schemas.AdminReviewOut)
def decide_admin_review(
    review_id: str,
    payload: schemas.AdminReviewDecision,
    db: Session = Depends(get_db),
    user: models.User = Depends(security.require_action("admin_review.decide")),
):
    if payload.status not in ("approved", "rejected"):
        raise HTTPException(status_code=400, detail="status must be approved or rejected")
    review = db.query(models.AdminReview).filter(models.AdminReview.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    review.status = payload.status
    review.decision_reason = payload.reason
    review.decided_by_id = user.id
    review.decided_at = datetime.datetime.utcnow()

    log_event(db, case_id=review.case_id, document_id=review.document_id, actor_id=user.id,
              event_type="admin_review_decided",
              details=f"Submission ({review.doc_type}) {payload.status} by Admin")

    db.commit()
    db.refresh(review)
    return _to_out(review)
