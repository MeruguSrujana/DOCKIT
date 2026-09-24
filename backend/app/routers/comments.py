from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from .. import models, schemas, security
from ..database import get_db

router = APIRouter(prefix="/comments", tags=["comments"])


@router.post("", response_model=schemas.CommentOut)
def create_comment(
    payload: schemas.CommentCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(security.require_action("comment.create")),
):
    case = db.query(models.Case).filter(models.Case.id == payload.case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    if payload.document_id:
        doc = db.query(models.Document).filter(models.Document.id == payload.document_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

    comment = models.Comment(
        case_id=payload.case_id,
        document_id=payload.document_id,
        author_id=user.id,
        content=payload.content,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return schemas.CommentOut(
        id=comment.id, case_id=comment.case_id, document_id=comment.document_id,
        author_name=user.full_name, content=comment.content, created_at=comment.created_at,
    )


@router.get("/case/{case_id}", response_model=List[schemas.CommentOut])
def list_case_comments(
    case_id: str,
    document_id: str = None,
    db: Session = Depends(get_db),
    user: models.User = Depends(security.get_current_user),
):
    q = db.query(models.Comment).filter(models.Comment.case_id == case_id)
    if document_id:
        q = q.filter(models.Comment.document_id == document_id)
    comments = q.order_by(models.Comment.created_at.asc()).all()
    return [
        schemas.CommentOut(id=c.id, case_id=c.case_id, document_id=c.document_id,
                            author_name=c.author.full_name, content=c.content, created_at=c.created_at)
        for c in comments
    ]
