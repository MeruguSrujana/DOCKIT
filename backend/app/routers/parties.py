from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from .. import models, schemas, security
from ..database import get_db
from ..events import log_event

router = APIRouter(prefix="/parties", tags=["parties"])


@router.post("", response_model=schemas.PartyOut)
def create_party(
    payload: schemas.PartyCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(security.require_action("party.create")),
):
    case = db.query(models.Case).filter(models.Case.id == payload.case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    if payload.matter_id:
        matter = db.query(models.CaseMatter).filter(
            models.CaseMatter.id == payload.matter_id,
            models.CaseMatter.case_id == payload.case_id,
        ).first()
        if not matter:
            raise HTTPException(status_code=400, detail="Matter does not belong to this case")

    party = models.CaseParty(
        case_id=payload.case_id,
        matter_id=payload.matter_id,
        party_role=payload.party_role,
        name=payload.name,
        contact=payload.contact,
        notes=payload.notes,
        created_by_id=user.id,
    )
    db.add(party)
    db.flush()
    log_event(db, case_id=case.id, actor_id=user.id, event_type="party_added",
              details=f"{payload.party_role}: {payload.name}")
    db.commit()
    db.refresh(party)
    return party


@router.get("/case/{case_id}", response_model=List[schemas.PartyOut])
def list_case_parties(case_id: str, db: Session = Depends(get_db),
                       user: models.User = Depends(security.get_current_user)):
    return db.query(models.CaseParty).filter(models.CaseParty.case_id == case_id).all()
