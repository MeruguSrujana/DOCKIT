from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from .. import models, schemas, security
from ..database import get_db
from ..events import log_event, notify

router = APIRouter(prefix="/cases", tags=["collaborators"])


@router.get("/{case_id}/collaborators", response_model=List[schemas.CollaboratorOut])
def list_collaborators(case_id: str, db: Session = Depends(get_db),
                        user: models.User = Depends(security.get_current_user)):
    rows = db.query(models.CaseCollaborator).filter(models.CaseCollaborator.case_id == case_id).all()
    return [
        schemas.CollaboratorOut(
            id=r.id, case_id=r.case_id, user_id=r.user_id, user_name=r.user.full_name,
            role_label=r.role_label, added_by_name=r.added_by.full_name, added_at=r.added_at,
        ) for r in rows
    ]


@router.post("/{case_id}/collaborators", response_model=schemas.CollaboratorOut)
def add_collaborator(
    case_id: str,
    payload: schemas.CollaboratorCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(security.require_action("case.manage_collaborators")),
):
    case = db.query(models.Case).filter(models.Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    target = db.query(models.User).filter(models.User.id == payload.user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    existing = db.query(models.CaseCollaborator).filter(
        models.CaseCollaborator.case_id == case_id,
        models.CaseCollaborator.user_id == payload.user_id,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="This person already has access to the case")

    collab = models.CaseCollaborator(
        case_id=case_id, user_id=payload.user_id,
        role_label=payload.role_label, added_by_id=user.id,
    )
    db.add(collab)
    db.flush()
    log_event(db, case_id=case_id, actor_id=user.id, event_type="collaborator_added",
              details=f"{target.full_name} added to case ({payload.role_label})")
    notify(db, user_id=target.id, notif_type="case_access_granted",
           message=f"You were added to case {case.case_number} as {payload.role_label}",
           case_id=case_id)
    db.commit()
    db.refresh(collab)
    return schemas.CollaboratorOut(
        id=collab.id, case_id=collab.case_id, user_id=collab.user_id, user_name=target.full_name,
        role_label=collab.role_label, added_by_name=user.full_name, added_at=collab.added_at,
    )


@router.delete("/{case_id}/collaborators/{collaborator_id}")
def remove_collaborator(
    case_id: str,
    collaborator_id: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(security.require_action("case.manage_collaborators")),
):
    collab = db.query(models.CaseCollaborator).filter(
        models.CaseCollaborator.id == collaborator_id,
        models.CaseCollaborator.case_id == case_id,
    ).first()
    if not collab:
        raise HTTPException(status_code=404, detail="Collaborator not found")
    removed_name = collab.user.full_name
    db.delete(collab)
    log_event(db, case_id=case_id, actor_id=user.id, event_type="collaborator_removed",
              details=f"{removed_name} removed from case")
    db.commit()
    return {"status": "removed"}
