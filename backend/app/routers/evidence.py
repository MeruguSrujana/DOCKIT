from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from .. import models, schemas, security, workflow
from ..database import get_db
from ..events import log_event

router = APIRouter(prefix="/evidence", tags=["evidence"])


@router.post("", response_model=schemas.EvidenceOut)
def create_evidence(
    payload: schemas.EvidenceCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(security.require_action("evidence.create")),
):
    case = db.query(models.Case).filter(models.Case.id == payload.case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    security.check_case_access(db, case, user)
    existing = db.query(models.Evidence).filter(models.Evidence.evidence_code == payload.evidence_code).first()
    if existing:
        raise HTTPException(status_code=400, detail="Evidence code already exists")

    ev = models.Evidence(
        evidence_code=payload.evidence_code,
        case_id=case.id,
        matter_id=payload.matter_id,
        description=payload.description,
        seizure_reference=payload.seizure_reference,
        linked_document_id=payload.linked_document_id,
        created_by_id=user.id,
    )
    db.add(ev)
    db.flush()
    log_event(db, case_id=case.id, evidence_id=ev.id, actor_id=user.id,
              event_type="created", to_state="collected",
              details=f"Evidence {ev.evidence_code} registered")
    db.commit()
    db.refresh(ev)
    return ev


@router.get("/case/{case_id}", response_model=List[schemas.EvidenceOut])
def list_case_evidence(case_id: str, db: Session = Depends(get_db),
                        user: models.User = Depends(security.get_current_user)):
    case = db.query(models.Case).filter(models.Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    security.check_case_access(db, case, user)
    return db.query(models.Evidence).filter(models.Evidence.case_id == case_id).all()


@router.post("/{evidence_id}/transition", response_model=schemas.EvidenceOut)
def transition_evidence(
    evidence_id: str,
    payload: schemas.TransitionRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(security.require_action("evidence.update_status")),
):
    ev = db.query(models.Evidence).filter(models.Evidence.id == evidence_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence not found")

    from_state = ev.status
    to_state = workflow.apply_transition(workflow.EVIDENCE_TRANSITIONS, ev.status, payload.action)
    ev.status = to_state

    log_event(db, case_id=ev.case_id, evidence_id=ev.id, actor_id=user.id,
              event_type=f"evidence_{payload.action}", from_state=from_state, to_state=to_state,
              details=payload.reason)
    db.commit()
    db.refresh(ev)
    return ev
