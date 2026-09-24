from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from .. import models, schemas, security
from ..database import get_db

router = APIRouter(prefix="/templates", tags=["templates"])


@router.get("", response_model=List[schemas.TemplateOut])
def list_templates(db: Session = Depends(get_db), user: models.User = Depends(security.get_current_user)):
    return db.query(models.DocumentTemplate).all()


@router.get("/{template_id}", response_model=schemas.TemplateOut)
def get_template(template_id: str, db: Session = Depends(get_db),
                  user: models.User = Depends(security.get_current_user)):
    tpl = db.query(models.DocumentTemplate).filter(models.DocumentTemplate.id == template_id).first()
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")
    return tpl
