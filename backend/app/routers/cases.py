from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from .. import models, schemas, security
from ..database import get_db
from ..events import log_event

router = APIRouter(prefix="/cases", tags=["cases"])


@router.post("", response_model=schemas.CaseOut)
def create_case(
    payload: schemas.CaseCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(security.require_action("case.create")),
):
    existing = db.query(models.Case).filter(models.Case.case_number == payload.case_number).first()
    if existing:
        raise HTTPException(status_code=400, detail="Case number already exists")
    # Case-type-driven jurisdiction requirement: criminal case types need
    # a Police Station on record; land/revenue disputes need a Revenue
    # Office. This is enforced server-side, not just hinted in the form.
    LAND_REVENUE_TYPES = {"land_dispute", "revenue_dispute"}
    if payload.case_type in LAND_REVENUE_TYPES:
        if not payload.revenue_office:
            raise HTTPException(status_code=400, detail="This case type requires a Revenue Office")
    else:
        if not payload.police_station:
            raise HTTPException(status_code=400, detail="This case type requires a Police Station")

    jurisdiction_label = payload.jurisdiction or ", ".join(
        p for p in [payload.police_station or payload.revenue_office, payload.mandal, payload.district] if p
    )

    case = models.Case(
        case_number=payload.case_number,
        case_type=payload.case_type,
        jurisdiction=jurisdiction_label,
        district=payload.district,
        mandal=payload.mandal,
        police_station=payload.police_station,
        revenue_office=payload.revenue_office,
        priority=payload.priority,
        source=payload.source,
        created_by_id=user.id,
    )
    db.add(case)
    db.flush()
    log_event(db, case_id=case.id, actor_id=user.id, event_type="created",
              details=f"Case {case.case_number} created")
    db.commit()
    db.refresh(case)
    return case


@router.get("", response_model=List[schemas.CaseOut])
def list_cases(db: Session = Depends(get_db), user: models.User = Depends(security.get_current_user)):
    cases = db.query(models.Case).order_by(models.Case.created_at.desc()).all()
    if user.role.name == "admin":
        return cases
    collaborator_case_ids = {
        c.case_id for c in db.query(models.CaseCollaborator).filter(
            models.CaseCollaborator.user_id == user.id
        ).all()
    }
    return [
        c for c in cases
        if not c.is_restricted
        or user.id in (c.created_by_id, c.owner_id)
        or c.id in collaborator_case_ids
    ]


@router.get("/{case_id}", response_model=schemas.CaseOut)
def get_case(case_id: str, db: Session = Depends(get_db), user: models.User = Depends(security.get_current_user)):
    case = db.query(models.Case).filter(models.Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    security.check_case_access(db, case, user)
    return case


def _get_case_or_404(db: Session, case_id: str) -> models.Case:
    case = db.query(models.Case).filter(models.Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


@router.post("/{case_id}/owner", response_model=schemas.CaseOut)
def assign_owner(
    case_id: str,
    payload: schemas.OwnerAssignRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(security.require_action("case.assign_owner")),
):
    case = _get_case_or_404(db, case_id)
    owner = db.query(models.User).filter(models.User.id == payload.owner_id).first()
    if not owner:
        raise HTTPException(status_code=404, detail="Owner user not found")
    case.owner_id = owner.id
    log_event(db, case_id=case.id, actor_id=user.id, event_type="owner_assigned",
              details=f"Case owner assigned to {owner.full_name}")
    db.commit()
    db.refresh(case)
    return case


@router.post("/{case_id}/retention", response_model=schemas.CaseOut)
def set_retention(
    case_id: str,
    payload: schemas.RetentionSetRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(security.require_action("case.set_retention")),
):
    case = _get_case_or_404(db, case_id)
    case.retention_date = payload.retention_date
    log_event(db, case_id=case.id, actor_id=user.id, event_type="retention_set",
              details=f"Retention date set to {payload.retention_date.isoformat()}")
    db.commit()
    db.refresh(case)
    return case


@router.post("/{case_id}/dispose", response_model=schemas.CaseOut)
def dispose_case(
    case_id: str,
    payload: schemas.DisposalRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(security.require_action("case.dispose")),
):
    case = _get_case_or_404(db, case_id)
    if payload.disposal_status not in ("pending_disposal", "disposed"):
        raise HTTPException(status_code=400, detail="disposal_status must be pending_disposal or disposed")
    if case.legal_hold and payload.disposal_status == "disposed":
        raise HTTPException(status_code=409, detail="Case is under legal hold — cannot be disposed")
    from_state = case.disposal_status
    case.disposal_status = payload.disposal_status
    log_event(db, case_id=case.id, actor_id=user.id, event_type="disposal_status_changed",
              from_state=from_state, to_state=payload.disposal_status, details=payload.reason)
    db.commit()
    db.refresh(case)
    return case


@router.post("/{case_id}/active-status", response_model=schemas.CaseOut)
def set_active_status(
    case_id: str,
    payload: schemas.ActiveStatusRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(security.require_action("case.set_active_status")),
):
    case = _get_case_or_404(db, case_id)
    case.is_active = payload.is_active
    case.status = "active" if payload.is_active else "closed"
    log_event(db, case_id=case.id, actor_id=user.id,
              event_type="activated" if payload.is_active else "deactivated", details=payload.reason)
    db.commit()
    db.refresh(case)
    return case


@router.post("/{case_id}/restrict", response_model=schemas.CaseOut)
def set_restricted(
    case_id: str,
    payload: schemas.RestrictedSetRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(security.require_action("case.set_restricted")),
):
    case = _get_case_or_404(db, case_id)
    case.is_restricted = payload.is_restricted
    log_event(db, case_id=case.id, actor_id=user.id,
              event_type="restricted" if payload.is_restricted else "unrestricted",
              details="Case marked restricted" if payload.is_restricted else "Case restriction lifted")
    db.commit()
    db.refresh(case)
    return case


# The canonical stage sequence shown in Admin's flow overview. Deliberately
# status-only — Admin sees which stage a case has reached, never the
# document content behind it.
FLOW_STAGES = [
    ("FIR", "fir"),
    ("Seizure Memo", "seizure_memo"),
    ("Forensic Request", "forensic_request"),
    ("Forensic Report", "forensic_report"),
    ("Witness Statement", "witness_statement"),
    ("Charge Sheet", "charge_sheet"),
    ("Court Filing", "court_filing"),
]


@router.get("/{case_id}/flow", response_model=schemas.CaseFlowOut)
def case_flow(case_id: str, db: Session = Depends(get_db),
              user: models.User = Depends(security.get_current_user)):
    """Status-only overview of where the case has reached in each
    canonical document stage. No document content is included or
    queried here — only doc_type + status."""
    case = _get_case_or_404(db, case_id)
    docs = db.query(models.Document).filter(models.Document.case_id == case_id).all()
    latest_by_type = {}
    for d in docs:
        existing = latest_by_type.get(d.doc_type)
        if not existing or d.created_at > existing.created_at:
            latest_by_type[d.doc_type] = d

    stages = []
    for label, doc_type in FLOW_STAGES:
        doc = latest_by_type.get(doc_type)
        stages.append(schemas.CaseFlowStage(
            stage=label, doc_type=doc_type,
            status=doc.status if doc else "not_started",
        ))
    return schemas.CaseFlowOut(case_id=case_id, stages=stages)
