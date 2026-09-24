from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .. import models, security
from ..database import get_db
from ..events import log_event

router = APIRouter(prefix="/adapters", tags=["adapters (mocked)"])


class AdapterRequest(BaseModel):
    case_id: str
    document_id: str


@router.post("/mock-cctns/receive")
def mock_cctns_receive(
    payload: AdapterRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(security.require_action("adapter.trigger")),
):
    """SIMULATED. Represents an inbound acknowledgement that a document's
    reference (e.g. the FIR) has been cross-registered in CCTNS. No real
    government API is called — this endpoint exists to demonstrate the
    adapter boundary the architecture requires, isolated from core logic."""
    doc = db.query(models.Document).filter(models.Document.id == payload.document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    event = log_event(
        db, case_id=payload.case_id, document_id=payload.document_id, actor_id=user.id,
        event_type="adapter_inbound", source="Mock CCTNS", destination="DOCKIT",
        details="Simulated: document cross-registered in CCTNS (mock adapter, no live government API).",
    )
    db.commit()
    return {"status": "simulated_receipt_logged", "event_id": event.id}


@router.post("/mock-ecourts/send")
def mock_ecourts_send(
    payload: AdapterRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(security.require_action("adapter.trigger")),
):
    """SIMULATED. Represents an outbound notification that a document has
    been made available to the court system. No real e-Courts API is
    called."""
    doc = db.query(models.Document).filter(models.Document.id == payload.document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    event = log_event(
        db, case_id=payload.case_id, document_id=payload.document_id, actor_id=user.id,
        event_type="adapter_outbound", source="DOCKIT", destination="Mock e-Courts",
        details="Simulated: document made available to e-Courts (mock adapter, no live government API).",
    )
    db.commit()
    return {"status": "simulated_send_logged", "event_id": event.id}
