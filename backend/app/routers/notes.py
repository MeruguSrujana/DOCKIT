from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from .. import models, schemas, security
from ..database import get_db

router = APIRouter(prefix="/notes", tags=["notes"])


@router.post("", response_model=schemas.NoteOut)
def create_note(
    payload: schemas.NoteCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(security.require_action("note.create")),
):
    case = db.query(models.Case).filter(models.Case.id == payload.case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    note = models.CaseNote(
        case_id=payload.case_id,
        author_id=user.id,
        content=payload.content,
        pinned=payload.pinned,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return schemas.NoteOut(
        id=note.id, case_id=note.case_id, author_name=user.full_name,
        content=note.content, pinned=note.pinned, created_at=note.created_at,
    )


@router.get("/case/{case_id}", response_model=List[schemas.NoteOut])
def list_case_notes(case_id: str, db: Session = Depends(get_db),
                     user: models.User = Depends(security.get_current_user)):
    notes = db.query(models.CaseNote).filter(models.CaseNote.case_id == case_id) \
        .order_by(models.CaseNote.pinned.desc(), models.CaseNote.created_at.desc()).all()
    return [
        schemas.NoteOut(id=n.id, case_id=n.case_id, author_name=n.author.full_name,
                         content=n.content, pinned=n.pinned, created_at=n.created_at)
        for n in notes
    ]
