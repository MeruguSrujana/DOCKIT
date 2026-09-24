from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List

from .. import models, security
from ..database import get_db

router = APIRouter(prefix="/search", tags=["search"])


def _accessible_case_ids(db: Session, user: models.User):
    """Same reachability rule as the case list: Admin sees everything,
    everyone else is limited to non-restricted cases plus any case they
    created/own/are a collaborator on. Search must never leak a
    restricted case's contents to someone who couldn't open it directly."""
    if user.role.name == "admin":
        return None  # None = no filter, all cases
    collaborator_ids = {
        c.case_id for c in db.query(models.CaseCollaborator).filter(
            models.CaseCollaborator.user_id == user.id
        ).all()
    }
    cases = db.query(models.Case).all()
    return {
        c.id for c in cases
        if not c.is_restricted or user.id in (c.created_by_id, c.owner_id) or c.id in collaborator_ids
    }


@router.get("")
def search(
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    user: models.User = Depends(security.get_current_user),
):
    """Unified keyword search across cases, documents, evidence, parties,
    notes and matters -- intended as a fast "type a name/word, jump to
    it" lookup rather than a document-content search (document content
    is stored as hashed version blobs, not indexed text, so this does
    not search inside document bodies). This is substring/keyword
    matching, not vector/embedding-based semantic search.

    Store & Archive: closed/archived cases stay findable. Access-
    controlled: restricted cases the user can't open are excluded.
    """
    like = f"%{q}%"
    allowed_ids = _accessible_case_ids(db, user)

    def case_filter(query, case_id_col):
        if allowed_ids is None:
            return query
        return query.filter(case_id_col.in_(allowed_ids))

    cases_q = db.query(models.Case).filter(
        or_(models.Case.case_number.ilike(like), models.Case.jurisdiction.ilike(like),
            models.Case.case_type.ilike(like))
    )
    if allowed_ids is not None:
        cases_q = cases_q.filter(models.Case.id.in_(allowed_ids))
    cases = cases_q.limit(20).all()

    documents = case_filter(
        db.query(models.Document).filter(
            or_(models.Document.doc_ref.ilike(like), models.Document.title.ilike(like),
                models.Document.doc_type.ilike(like))
        ),
        models.Document.case_id,
    ).limit(20).all()

    evidence = case_filter(
        db.query(models.Evidence).filter(
            or_(models.Evidence.evidence_code.ilike(like), models.Evidence.description.ilike(like))
        ),
        models.Evidence.case_id,
    ).limit(20).all()

    parties = case_filter(
        db.query(models.CaseParty).filter(
            or_(models.CaseParty.name.ilike(like), models.CaseParty.party_role.ilike(like))
        ),
        models.CaseParty.case_id,
    ).limit(20).all()

    notes = case_filter(
        db.query(models.CaseNote).filter(models.CaseNote.content.ilike(like)),
        models.CaseNote.case_id,
    ).limit(20).all()

    matters = case_filter(
        db.query(models.CaseMatter).filter(
            or_(models.CaseMatter.title.ilike(like), models.CaseMatter.description.ilike(like),
                models.CaseMatter.location.ilike(like))
        ),
        models.CaseMatter.case_id,
    ).limit(20).all()

    return {
        "query": q,
        "cases": [{"id": c.id, "case_number": c.case_number, "status": c.status,
                   "disposal_status": c.disposal_status} for c in cases],
        "documents": [{"id": d.id, "doc_ref": d.doc_ref, "title": d.title, "doc_type": d.doc_type,
                        "status": d.status, "case_id": d.case_id} for d in documents],
        "evidence": [{"id": e.id, "evidence_code": e.evidence_code, "description": e.description,
                       "status": e.status, "case_id": e.case_id} for e in evidence],
        "parties": [{"id": p.id, "name": p.name, "party_role": p.party_role,
                      "case_id": p.case_id} for p in parties],
        "notes": [{"id": n.id, "content": n.content[:120], "case_id": n.case_id} for n in notes],
        "matters": [{"id": m.id, "title": m.title, "case_id": m.case_id} for m in matters],
    }
