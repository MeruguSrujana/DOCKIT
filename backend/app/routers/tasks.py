import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from .. import models, schemas, security
from ..database import get_db
from ..events import log_event, notify

router = APIRouter(prefix="/tasks", tags=["tasks"])

VALID_STATUSES = {"pending", "in_progress", "done", "cancelled"}


@router.post("", response_model=schemas.TaskOut)
def create_task(
    payload: schemas.TaskCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(security.require_action("task.create")),
):
    case = db.query(models.Case).filter(models.Case.id == payload.case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    task = models.Task(
        case_id=payload.case_id,
        title=payload.title,
        description=payload.description,
        assigned_to_id=payload.assigned_to_id,
        assigned_by_id=user.id,
        due_date=payload.due_date,
    )
    db.add(task)
    db.flush()
    log_event(db, case_id=case.id, actor_id=user.id, event_type="task_created",
              details=f"Task '{payload.title}' created")
    if payload.assigned_to_id:
        notify(db, user_id=payload.assigned_to_id, notif_type="task_assigned",
               message=f"You were assigned task '{payload.title}' on case {case.case_number}",
               case_id=case.id)
    db.commit()
    db.refresh(task)
    return task


@router.get("/case/{case_id}", response_model=List[schemas.TaskOut])
def list_case_tasks(case_id: str, db: Session = Depends(get_db),
                     user: models.User = Depends(security.get_current_user)):
    return db.query(models.Task).filter(models.Task.case_id == case_id) \
        .order_by(models.Task.created_at.desc()).all()


@router.get("/mine", response_model=List[schemas.TaskOut])
def list_my_tasks(db: Session = Depends(get_db), user: models.User = Depends(security.get_current_user)):
    return db.query(models.Task).filter(models.Task.assigned_to_id == user.id) \
        .order_by(models.Task.due_date.asc().nullslast()).all()


@router.patch("/{task_id}", response_model=schemas.TaskOut)
def update_task(
    task_id: str,
    payload: schemas.TaskUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(security.require_action("task.update")),
):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if payload.status is not None:
        if payload.status not in VALID_STATUSES:
            raise HTTPException(status_code=400, detail=f"status must be one of {sorted(VALID_STATUSES)}")
        from_status = task.status
        task.status = payload.status
        if payload.status == "done":
            task.completed_at = datetime.datetime.utcnow()
        log_event(db, case_id=task.case_id, actor_id=user.id, event_type="task_status_changed",
                  from_state=from_status, to_state=payload.status, details=task.title)

    if payload.title is not None:
        task.title = payload.title
    if payload.description is not None:
        task.description = payload.description
    if payload.due_date is not None:
        task.due_date = payload.due_date
    if payload.assigned_to_id is not None:
        task.assigned_to_id = payload.assigned_to_id
        notify(db, user_id=payload.assigned_to_id, notif_type="task_assigned",
               message=f"You were assigned task '{task.title}'", case_id=task.case_id)

    db.commit()
    db.refresh(task)
    return task
