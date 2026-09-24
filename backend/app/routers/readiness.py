from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from .. import models, schemas, security
from ..database import get_db

router = APIRouter(prefix="/readiness", tags=["readiness"])

# Which document types a "crime_against_women" case type is expected to
# accumulate, used only to compute the checklist below. Rule-based, not
# a trained model — deliberately, per the architecture's AI constraints.
EXPECTED_DOC_TYPES = {
    "crime_against_women": ["fir", "witness_statement", "forensic_report", "charge_sheet"],
    "cyber_crime": ["fir", "witness_statement", "forensic_report", "charge_sheet"],
    "road_accident": ["fir", "witness_statement", "forensic_report", "charge_sheet"],
}


@router.get("/case/{case_id}", response_model=schemas.ReadinessOut)
def case_readiness(case_id: str, db: Session = Depends(get_db),
                    user: models.User = Depends(security.get_current_user)):
    case = db.query(models.Case).filter(models.Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    docs = db.query(models.Document).filter(models.Document.case_id == case_id).all()
    total = len(docs)
    approved = sum(1 for d in docs if d.status in ("approved", "transferred", "received", "archived"))
    pending_review = sum(1 for d in docs if d.status == "under_review")

    integrity_failures = db.query(models.Event).filter(
        models.Event.case_id == case_id, models.Event.event_type == "integrity_failure"
    ).count()

    version_conflicts = 0
    for d in docs:
        active_versions = [v for v in d.versions if not v.superseded]
        if len(active_versions) > 1:
            version_conflicts += 1

    last_event = db.query(models.Event).filter(models.Event.case_id == case_id) \
        .order_by(models.Event.timestamp.desc()).first()

    expected_types = EXPECTED_DOC_TYPES.get(case.case_type, [])
    present_types = {d.doc_type for d in docs if d.status != "draft"}
    checklist = {t: (t in present_types) for t in expected_types}

    completeness_pct = int(round((approved / total) * 100)) if total else 0

    if pending_review > 0:
        next_action = f"{pending_review} document(s) awaiting review/approval"
    elif integrity_failures > 0:
        next_action = f"{integrity_failures} integrity failure(s) require investigation"
    elif any(not v for v in checklist.values()):
        missing = [t for t, present in checklist.items() if not present]
        next_action = f"Missing expected document type(s): {', '.join(missing)}"
    else:
        next_action = None

    return schemas.ReadinessOut(
        case_id=case_id,
        total_documents=total,
        approved_documents=approved,
        pending_review=pending_review,
        pending_approval_count=pending_review,
        integrity_failures=integrity_failures,
        version_conflicts=version_conflicts,
        last_activity=last_event.timestamp if last_event else None,
        completeness_pct=completeness_pct,
        next_required_action=next_action,
        checklist=checklist,
    )
