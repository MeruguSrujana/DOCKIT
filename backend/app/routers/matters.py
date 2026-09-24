from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from .. import models, schemas, security
from ..database import get_db
from ..events import log_event

router = APIRouter(prefix="/matters", tags=["matters"])


def _to_out(db: Session, m: models.CaseMatter) -> schemas.MatterOut:
    doc_count = db.query(models.Document).filter(models.Document.matter_id == m.id).count()
    ev_count = db.query(models.Evidence).filter(models.Evidence.matter_id == m.id).count()
    witness_count = db.query(models.CaseParty).filter(
        models.CaseParty.matter_id == m.id, models.CaseParty.party_role == "witness"
    ).count()
    return schemas.MatterOut(
        id=m.id, case_id=m.case_id, title=m.title, key_question=m.key_question, status=m.status,
        description=m.description, matter_date=m.matter_date, location=m.location,
        created_by_name=m.created_by.full_name, created_at=m.created_at,
        document_count=doc_count, evidence_count=ev_count, witness_count=witness_count,
    )


@router.post("", response_model=schemas.MatterOut)
def create_matter(
    payload: schemas.MatterCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(security.require_action("matter.create")),
):
    case = db.query(models.Case).filter(models.Case.id == payload.case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    security.check_case_access(db, case, user)

    matter = models.CaseMatter(
        case_id=payload.case_id, title=payload.title, key_question=payload.key_question,
        status=payload.status, description=payload.description,
        matter_date=payload.matter_date, location=payload.location, created_by_id=user.id,
    )
    db.add(matter)
    db.flush()
    log_event(db, case_id=case.id, actor_id=user.id, event_type="matter_created",
              details=f"Matter '{payload.title}' created")
    db.commit()
    db.refresh(matter)
    return _to_out(db, matter)


@router.get("/case/{case_id}", response_model=List[schemas.MatterOut])
def list_case_matters(case_id: str, db: Session = Depends(get_db),
                       user: models.User = Depends(security.get_current_user)):
    case = db.query(models.Case).filter(models.Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    security.check_case_access(db, case, user)
    matters = db.query(models.CaseMatter).filter(models.CaseMatter.case_id == case_id) \
        .order_by(models.CaseMatter.created_at.desc()).all()
    return [_to_out(db, m) for m in matters]


@router.get("/{matter_id}/documents", response_model=List[schemas.DocumentOut])
def matter_documents(matter_id: str, db: Session = Depends(get_db),
                      user: models.User = Depends(security.get_current_user)):
    return db.query(models.Document).filter(models.Document.matter_id == matter_id).all()


@router.get("/{matter_id}/evidence", response_model=List[schemas.EvidenceOut])
def matter_evidence(matter_id: str, db: Session = Depends(get_db),
                     user: models.User = Depends(security.get_current_user)):
    return db.query(models.Evidence).filter(models.Evidence.matter_id == matter_id).all()


@router.get("/{matter_id}/witnesses", response_model=List[schemas.PartyOut])
def matter_witnesses(matter_id: str, db: Session = Depends(get_db),
                      user: models.User = Depends(security.get_current_user)):
    return db.query(models.CaseParty).filter(
        models.CaseParty.matter_id == matter_id, models.CaseParty.party_role == "witness"
    ).all()


@router.post("/{matter_id}/status", response_model=schemas.MatterOut)
def set_matter_status(
    matter_id: str,
    payload: schemas.MatterStatusUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(security.require_action("matter.create")),
):
    matter = db.query(models.CaseMatter).filter(models.CaseMatter.id == matter_id).first()
    if not matter:
        raise HTTPException(status_code=404, detail="Matter not found")
    matter.status = payload.status
    log_event(db, case_id=matter.case_id, actor_id=user.id, event_type="matter_status_changed",
              details=f"Matter '{matter.title}' status set to {payload.status}")
    db.commit()
    db.refresh(matter)
    return _to_out(db, matter)


@router.post("/assign/document/{document_id}", response_model=schemas.DocumentOut)
def assign_document_matter(
    document_id: str,
    payload: schemas.AssignMatterRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(security.require_action("matter.assign")),
):
    doc = db.query(models.Document).filter(models.Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    doc.matter_id = payload.matter_id
    log_event(db, case_id=doc.case_id, document_id=doc.id, actor_id=user.id,
              event_type="matter_assigned",
              details=f"Document {doc.doc_ref} " + ("assigned to matter" if payload.matter_id else "unassigned from matter"))
    db.commit()
    db.refresh(doc)
    return doc


@router.post("/assign/evidence/{evidence_id}", response_model=schemas.EvidenceOut)
def assign_evidence_matter(
    evidence_id: str,
    payload: schemas.AssignMatterRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(security.require_action("matter.assign")),
):
    ev = db.query(models.Evidence).filter(models.Evidence.id == evidence_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence not found")
    ev.matter_id = payload.matter_id
    log_event(db, case_id=ev.case_id, evidence_id=ev.id, actor_id=user.id,
              event_type="matter_assigned",
              details=f"Evidence {ev.evidence_code} " + ("assigned to matter" if payload.matter_id else "unassigned from matter"))
    db.commit()
    db.refresh(ev)
    return ev
