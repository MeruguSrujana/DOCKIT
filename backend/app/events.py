from sqlalchemy.orm import Session
from . import models


def log_event(
    db: Session,
    case_id: str,
    actor_id: str,
    event_type: str,
    document_id: str = None,
    evidence_id: str = None,
    from_state: str = None,
    to_state: str = None,
    source: str = None,
    destination: str = None,
    details: str = None,
) -> models.Event:
    """The only function in the codebase that writes to the events table.
    Every mutating router calls this after (and only after) the underlying
    state change actually happened — the event is a record of something
    real, never a frontend label change. Nothing UPDATEs or DELETEs a
    row in this table anywhere in the application."""
    event = models.Event(
        case_id=case_id,
        document_id=document_id,
        evidence_id=evidence_id,
        event_type=event_type,
        actor_id=actor_id,
        from_state=from_state,
        to_state=to_state,
        source=source,
        destination=destination,
        details=details,
    )
    db.add(event)
    db.flush()
    return event


def notify(
    db: Session,
    user_id: str,
    notif_type: str,
    message: str,
    case_id: str = None,
    document_id: str = None,
) -> models.Notification:
    """Creates an in-app notification for a user. Distinct from log_event:
    an Event records what happened; a Notification records who was told
    about it. Never writes to the events table itself."""
    note = models.Notification(
        user_id=user_id,
        case_id=case_id,
        document_id=document_id,
        notif_type=notif_type,
        message=message,
    )
    db.add(note)
    db.flush()
    return note
