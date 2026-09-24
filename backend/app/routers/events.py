from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Optional

from .. import models, schemas, security
from ..database import get_db

router = APIRouter(prefix="/events", tags=["events"])


@router.get("/case/{case_id}", response_model=List[schemas.EventOut])
def case_timeline(
    case_id: str,
    document_id: Optional[str] = None,
    db: Session = Depends(get_db),
    user: models.User = Depends(security.get_current_user),
):
    """The provenance timeline. This reads directly from the append-only
    events table — nothing here is assembled or guessed from other
    tables' current state; it is literally the recorded history."""
    q = db.query(models.Event).filter(models.Event.case_id == case_id)
    if document_id:
        q = q.filter(models.Event.document_id == document_id)
    events = q.order_by(models.Event.timestamp.asc()).all()
    return [
        schemas.EventOut(
            id=e.id, event_type=e.event_type, actor=e.actor.full_name, timestamp=e.timestamp,
            document_id=e.document_id, evidence_id=e.evidence_id,
            from_state=e.from_state, to_state=e.to_state,
            source=e.source, destination=e.destination, details=e.details,
        )
        for e in events
    ]
