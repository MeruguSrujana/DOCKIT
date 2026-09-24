from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import itertools

from .. import models, schemas, security, workflow, storage, policy
from ..database import get_db
from ..events import log_event, notify

router = APIRouter(prefix="/documents", tags=["documents"])

_seq_counter = itertools.count(1)


def _next_doc_ref(db: Session, case: models.Case) -> str:
    count = db.query(models.Document).filter(
        models.Document.case_id == case.id
    ).count()

    return f"DOC-{case.case_number}-{count + 1:03d}"


# ---------------------------------------------------------
# CREATE DOCUMENT
# ---------------------------------------------------------

@router.post("", response_model=schemas.DocumentOut)
def create_document(
    payload: schemas.DocumentCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(
        security.require_action("document.create")
    ),
):
    case = db.query(models.Case).filter(
        models.Case.id == payload.case_id
    ).first()

    if not case:
        raise HTTPException(
            status_code=404,
            detail="Case not found"
        )

    security.check_case_access(db, case, user)

    doc = models.Document(
        doc_ref=_next_doc_ref(db, case),
        case_id=case.id,
        matter_id=payload.matter_id,
        doc_type=payload.doc_type,
        title=payload.title,
        origin_type=payload.origin_type,
        template_id=payload.template_id,
        status="draft",
        created_by_id=user.id,
        current_holder_id=user.id,
    )

    db.add(doc)
    db.flush()

    storage_path, sha = storage.save_content(
        payload.initial_content.encode("utf-8")
    )

    version = models.DocumentVersion(
        document_id=doc.id,
        version_no=1,
        storage_path=storage_path,
        sha256_hash=sha,
        prev_version_hash=None,
        reason="Initial creation",
        created_by_id=user.id,
    )

    db.add(version)
    db.flush()

    # Content-blind Admin approval gate: every submission is queued here.
    # Admin decides based on metadata only — this row never carries content.
    admin_review = models.AdminReview(
        document_id=doc.id,
        case_id=case.id,
        doc_type=doc.doc_type,
        submitted_by_id=user.id,
    )
    db.add(admin_review)
    db.flush()
    for admin_user in db.query(models.User).join(models.Role).filter(models.Role.name == "admin").all():
        notify(db, user_id=admin_user.id, notif_type="admin_review_pending",
               message=f"New {doc.doc_type.replace('_', ' ')} submitted on case {case.case_number} — pending your approval",
               case_id=case.id, document_id=doc.id)

    log_event(
        db,
        case_id=case.id,
        document_id=doc.id,
        actor_id=user.id,
        event_type="created",
        to_state="draft",
        details=(
            f"Document {doc.doc_ref} ({doc.doc_type}) "
            f"created, version 1, hash {sha[:12]}..."
        ),
    )

    db.commit()
    db.refresh(doc)

    return doc


# ---------------------------------------------------------
# LIST DOCUMENTS IN A CASE
# ---------------------------------------------------------

@router.get(
    "/case/{case_id}",
    response_model=List[schemas.DocumentOut]
)
def list_case_documents(
    case_id: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(
        security.get_current_user
    ),
):
    case = db.query(models.Case).filter(models.Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    security.check_case_access(db, case, user)
    return (
        db.query(models.Document)
        .filter(models.Document.case_id == case_id)
        .all()
    )


# ---------------------------------------------------------
# MY INBOX — documents transferred to me, awaiting acknowledgment
# ---------------------------------------------------------
# Declared before /{document_id} so "inbox" isn't swallowed as an id.

@router.get("/inbox", response_model=List[schemas.InboxDocumentOut])
def my_inbox(db: Session = Depends(get_db), user: models.User = Depends(security.get_current_user)):
    docs = (
        db.query(models.Document)
        .filter(
            models.Document.current_holder_id == user.id,
            models.Document.status == "transferred",
        )
        .all()
    )
    return [
        schemas.InboxDocumentOut(
            id=d.id, doc_ref=d.doc_ref, doc_type=d.doc_type, title=d.title,
            status=d.status, case_id=d.case_id, case_number=d.case.case_number,
        )
        for d in docs
    ]


# ---------------------------------------------------------
# GET ONE DOCUMENT
# ---------------------------------------------------------

@router.get(
    "/{document_id}",
    response_model=schemas.DocumentOut
)
def get_document(
    document_id: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(
        security.get_current_user
    ),
):
    doc = (
        db.query(models.Document)
        .filter(models.Document.id == document_id)
        .first()
    )

    if not doc:
        raise HTTPException(
            status_code=404,
            detail="Document not found"
        )

    case = db.query(models.Case).filter(models.Case.id == doc.case_id).first()
    security.check_case_access(db, case, user)

    return doc


# ---------------------------------------------------------
# GET DOCUMENT CONTENT — the actual missing piece: every prior version
# of this API returned metadata (status, versions list, hashes) but
# never the readable content itself, for ANY role, including the
# uploader. This is what "open the document" actually needs.
# ---------------------------------------------------------

@router.get(
    "/{document_id}/content",
    response_model=schemas.DocumentContentOut,
)
def get_document_content(
    document_id: str,
    version_id: str = None,
    db: Session = Depends(get_db),
    user: models.User = Depends(security.get_current_user),
):
    doc = db.query(models.Document).filter(models.Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    case = db.query(models.Case).filter(models.Case.id == doc.case_id).first()
    security.check_case_access(db, case, user)

    if not security.can_view_document_content(db, doc, user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This document is locked. Request access to view the content.",
        )

    if version_id:
        version = next((v for v in doc.versions if v.id == version_id), None)
        if not version:
            raise HTTPException(status_code=404, detail="Version not found on this document")
    else:
        if not doc.versions:
            raise HTTPException(status_code=404, detail="This document has no versions yet")
        version = max(doc.versions, key=lambda v: v.version_no)

    content_bytes = storage.read_content(version.storage_path)

    # Auto-verify: every time content is opened, recompute the hash from
    # the bytes actually on disk and compare it to the hash recorded at
    # upload time. A tampered file is never silently served — this is
    # what makes integrity failures show up without anyone remembering
    # to click Verify by hand.
    recalculated = storage.recompute_hash(version.storage_path)
    if recalculated != version.sha256_hash:
        log_event(
            db, case_id=doc.case_id, document_id=doc.id, actor_id=user.id,
            event_type="integrity_failure",
            details=(
                f"Version {version.version_no}: content changed on disk. "
                f"recorded={version.sha256_hash[:12]}..., recalculated={recalculated[:12]}..."
            ),
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Integrity failure — this version's content has been modified since it was recorded. Content is blocked.",
        )

    content = content_bytes.decode("utf-8", errors="replace")

    return schemas.DocumentContentOut(
        document_id=doc.id, version_id=version.id, version_no=version.version_no,
        content=content, sha256_hash=version.sha256_hash,
    )


@router.get(
    "/{document_id}/lock-status",
    response_model=schemas.DocumentLockStatusOut,
)
def get_lock_status(
    document_id: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(security.get_current_user),
):
    """Lets the frontend decide, before trying to fetch content, whether
    to show the reader or the locked/request-access view."""
    doc = db.query(models.Document).filter(models.Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    case = db.query(models.Case).filter(models.Case.id == doc.case_id).first()
    security.check_case_access(db, case, user)

    is_owner = user.id == doc.created_by_id
    unlocked = is_owner or security.can_view_document_content(db, doc, user)

    my_request = (
        db.query(models.DocumentAccessRequest)
        .filter(
            models.DocumentAccessRequest.document_id == document_id,
            models.DocumentAccessRequest.requested_by_id == user.id,
        )
        .order_by(models.DocumentAccessRequest.created_at.desc())
        .first()
    )

    my_grant = None
    if my_request and my_request.status == "approved" and not my_request.revoked_at:
        import datetime as _dt
        if not my_request.expires_at or my_request.expires_at >= _dt.datetime.utcnow():
            my_grant = my_request

    return schemas.DocumentLockStatusOut(
        document_id=document_id, is_owner=is_owner, unlocked=unlocked,
        my_request_status=my_request.status if my_request else None,
        my_granted_mode=my_grant.granted_mode if my_grant else None,
        my_expires_at=my_grant.expires_at if my_grant else None,
    )


# ---------------------------------------------------------
# TRANSITION DOCUMENT
# ---------------------------------------------------------

@router.post(
    "/{document_id}/transition",
    response_model=schemas.DocumentOut
)
def transition_document(
    document_id: str,
    payload: schemas.TransitionRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(
        security.get_current_user
    ),
):
    doc = (
        db.query(models.Document)
        .filter(models.Document.id == document_id)
        .first()
    )

    if not doc:
        raise HTTPException(
            status_code=404,
            detail="Document not found"
        )

    # -----------------------------------------------------
    # POLICY ENGINE
    #
    # Checks:
    #   1. Who is the user?
    #   2. What state is the document in?
    #   3. What action are they trying to perform?
    # -----------------------------------------------------

    allowed = policy.is_allowed(
        user.role.name,
        doc.status,
        payload.action
    )

    if not allowed:
        # Record denied attempt in audit trail
        log_event(
            db,
            case_id=doc.case_id,
            document_id=doc.id,
            actor_id=user.id,
            event_type="permission_denied",
            from_state=doc.status,
            details=(
                f"Policy denied action '{payload.action}' "
                f"for role '{user.role.name}'."
            ),
        )

        db.commit()

        raise HTTPException(
            status_code=403,
            detail=(
                f"Policy denied: role '{user.role.name}' "
                f"cannot perform '{payload.action}' "
                f"when document is in '{doc.status}' state."
            ),
        )

    # -----------------------------------------------------
    # WORKFLOW ENGINE
    #
    # Policy says WHO may act.
    # Workflow says WHETHER the state transition is valid.
    # -----------------------------------------------------

    from_state = doc.status

    to_state = workflow.apply_transition(
        workflow.DOCUMENT_TRANSITIONS,
        doc.status,
        payload.action,
    )

    doc.status = to_state

    # -----------------------------------------------------
    # TRANSFER
    #
    # Example destination:
    # fo.rao
    #
    # The document becomes owned by that user.
    # -----------------------------------------------------

    if payload.action == "transfer":

        if not payload.destination:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Destination username is required "
                    "for transfer."
                ),
            )

        recipient = (
            db.query(models.User)
            .filter(
                models.User.username == payload.destination,
                models.User.is_active == True,
            )
            .first()
        )

        if not recipient:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Recipient '{payload.destination}' "
                    f"not found."
                ),
            )

        # Store the receiving user's ID.
        doc.current_holder_id = recipient.id

        notify(
            db, user_id=recipient.id, notif_type="document_transferred",
            message=f"{doc.doc_ref} ({doc.doc_type.replace('_', ' ')}) was transferred to you on case {doc.case.case_number} — open it to acknowledge receipt",
            case_id=doc.case_id, document_id=doc.id,
        )

    # -----------------------------------------------------
    # ACKNOWLEDGE RECEIPT
    # -----------------------------------------------------

    if payload.action == "acknowledge_receipt":

        doc.current_holder_id = user.id

    # -----------------------------------------------------
    # RECORD SUCCESSFUL ACTION
    # -----------------------------------------------------

    event_type = workflow.ACTION_TO_EVENT_TYPE.get(
        payload.action,
        payload.action,
    )

    log_event(
        db,
        case_id=doc.case_id,
        document_id=doc.id,
        actor_id=user.id,
        event_type=event_type,
        from_state=from_state,
        to_state=to_state,
        destination=(
            payload.destination
            if payload.action == "transfer"
            else None
        ),
        details=payload.reason,
    )

    db.commit()
    db.refresh(doc)

    return doc


# ---------------------------------------------------------
# CREATE NEW VERSION
# ---------------------------------------------------------

@router.post(
    "/{document_id}/versions",
    response_model=schemas.DocumentOut
)
def new_version(
    document_id: str,
    payload: schemas.NewVersionRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(
        security.require_action("document.new_version")
    ),
):
    doc = (
        db.query(models.Document)
        .filter(models.Document.id == document_id)
        .first()
    )

    if not doc:
        raise HTTPException(
            status_code=404,
            detail="Document not found"
        )

    latest = (
        max(
            doc.versions,
            key=lambda v: v.version_no
        )
        if doc.versions
        else None
    )

    # Mode enforcement: the owner can always create a new version. Anyone
    # else needs an active grant. In "edit" mode any new content is
    # allowed; in "append" mode the new content must start with exactly
    # the previous version's content — the server rejects any change to
    # existing text, it does not just hide the option in the UI.
    if user.id != doc.created_by_id:
        if security.can_edit_document_content(db, doc, user):
            pass
        elif security.can_append_document_content(db, doc, user):
            if latest:
                previous_bytes = storage.read_content(latest.storage_path)
                previous_text = previous_bytes.decode("utf-8", errors="replace")
                if not payload.content.startswith(previous_text):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Your access is Append-only: you may only add content to the end, not change what's already there.",
                    )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This document is locked. Request access to edit it.",
            )

    if latest:
        latest.superseded = True

    storage_path, sha = storage.save_content(
        payload.content.encode("utf-8")
    )

    version = models.DocumentVersion(
        document_id=doc.id,
        version_no=(
            latest.version_no + 1
            if latest
            else 1
        ),
        storage_path=storage_path,
        sha256_hash=sha,
        prev_version_hash=(
            latest.sha256_hash
            if latest
            else None
        ),
        reason=payload.reason,
        created_by_id=user.id,
    )

    db.add(version)
    db.flush()

    log_event(
        db,
        case_id=doc.case_id,
        document_id=doc.id,
        actor_id=user.id,
        event_type="version_created",
        details=(
            f"Version {version.version_no} created, "
            f"hash {sha[:12]}..., "
            f"reason: {payload.reason}"
        ),
    )

    db.commit()
    db.refresh(doc)

    return doc


# ---------------------------------------------------------
# VERIFY DOCUMENT INTEGRITY
# ---------------------------------------------------------

@router.post(
    "/{document_id}/versions/{version_id}/verify",
    response_model=schemas.IntegrityCheckResult
)
def verify_integrity(
    document_id: str,
    version_id: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(
        security.get_current_user
    ),
):
    version = (
        db.query(models.DocumentVersion)
        .filter(
            models.DocumentVersion.id == version_id,
            models.DocumentVersion.document_id == document_id,
        )
        .first()
    )

    if not version:
        raise HTTPException(
            status_code=404,
            detail="Version not found"
        )

    # Recalculate hash from stored content.
    recalculated = storage.recompute_hash(
        version.storage_path
    )

    verified = (
        recalculated == version.sha256_hash
    )

    doc = (
        db.query(models.Document)
        .filter(
            models.Document.id == document_id
        )
        .first()
    )

    log_event(
        db,
        case_id=doc.case_id,
        document_id=document_id,
        actor_id=user.id,
        event_type=(
            "integrity_check"
            if verified
            else "integrity_failure"
        ),
        details=(
            f"Version {version.version_no}: "
            f"recorded={version.sha256_hash[:12]}..., "
            f"recalculated={recalculated[:12]}..., "
            f"verified={verified}"
        ),
    )

    db.commit()

    return schemas.IntegrityCheckResult(
        document_id=document_id,
        version_id=version_id,
        version_no=version.version_no,
        recorded_hash=version.sha256_hash,
        recalculated_hash=recalculated,
        verified=verified,
    )