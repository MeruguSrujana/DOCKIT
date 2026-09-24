from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import datetime

from .. import models, schemas, security, storage
from ..database import get_db
from ..events import log_event

router = APIRouter(prefix="/disclosures", tags=["disclosures"])


def _to_out(r: models.DisclosureRequest) -> schemas.DisclosureOut:
    return schemas.DisclosureOut(
        id=r.id, case_id=r.case_id, document_id=r.document_id,
        doc_ref=r.document.doc_ref, doc_type=r.document.doc_type,
        requested_by_name=r.requested_by.full_name, reason=r.reason, status=r.status,
        decision_reason=r.decision_reason, created_at=r.created_at, decided_at=r.decided_at,
    )


@router.post("", response_model=schemas.DisclosureOut)
def request_disclosure(
    payload: schemas.DisclosureCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(security.require_action("disclosure.request")),
):
    """Only a Prosecutor or Court Clerk may raise this — the defence has
    zero access by default. This names exactly one document; approval
    releases only that document, never the whole case."""
    doc = db.query(models.Document).filter(
        models.Document.id == payload.document_id, models.Document.case_id == payload.case_id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found on this case")

    req = models.DisclosureRequest(
        case_id=payload.case_id, document_id=payload.document_id,
        requested_by_id=user.id, reason=payload.reason,
    )
    db.add(req)
    db.flush()
    log_event(db, case_id=payload.case_id, document_id=payload.document_id, actor_id=user.id,
              event_type="disclosure_requested",
              details=f"Disclosure requested for {doc.doc_ref} ({doc.doc_type})")
    db.commit()
    db.refresh(req)
    return _to_out(req)


@router.get("/case/{case_id}", response_model=List[schemas.DisclosureOut])
def list_case_disclosures(case_id: str, db: Session = Depends(get_db),
                           user: models.User = Depends(security.get_current_user)):
    rows = db.query(models.DisclosureRequest).filter(models.DisclosureRequest.case_id == case_id) \
        .order_by(models.DisclosureRequest.created_at.desc()).all()
    return [_to_out(r) for r in rows]


@router.post("/{disclosure_id}/decide", response_model=schemas.DisclosureOut)
def decide_disclosure(
    disclosure_id: str,
    payload: schemas.AdminReviewDecision,
    db: Session = Depends(get_db),
    user: models.User = Depends(security.require_action("disclosure.decide")),
):
    if payload.status not in ("approved", "rejected"):
        raise HTTPException(status_code=400, detail="status must be approved or rejected")
    req = db.query(models.DisclosureRequest).filter(models.DisclosureRequest.id == disclosure_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Disclosure request not found")

    req.status = payload.status
    req.decision_reason = payload.reason
    req.decided_by_id = user.id
    req.decided_at = datetime.datetime.utcnow()

    log_event(db, case_id=req.case_id, document_id=req.document_id, actor_id=user.id,
              event_type="disclosure_decided",
              details=f"Disclosure of {req.document.doc_ref} {payload.status} by Admin")

    db.commit()
    db.refresh(req)
    return _to_out(req)


@router.get("/case/{case_id}/released", response_model=List[schemas.DisclosedDocumentOut])
def list_released_documents(case_id: str, db: Session = Depends(get_db),
                             user: models.User = Depends(security.get_current_user)):
    """What the defence side actually sees: only documents that have an
    APPROVED disclosure request. No separate defence login exists yet in
    this prototype, so this endpoint stands in for that portal — it never
    returns anything beyond the specific approved document's content."""
    approved = db.query(models.DisclosureRequest).filter(
        models.DisclosureRequest.case_id == case_id,
        models.DisclosureRequest.status == "approved",
    ).all()
    out = []
    for r in approved:
        doc = r.document
        latest = max(doc.versions, key=lambda v: v.version_no) if doc.versions else None
        content = storage.read_content(latest.storage_path).decode("utf-8", errors="replace") if latest else ""
        out.append(schemas.DisclosedDocumentOut(
            document_id=doc.id, doc_ref=doc.doc_ref, doc_type=doc.doc_type,
            title=doc.title, content=content, disclosed_at=r.decided_at,
        ))
    return out
