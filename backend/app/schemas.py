import datetime
from typing import Optional, List, Any
from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    full_name: str


class UserOut(BaseModel):
    id: str
    username: str
    full_name: str
    role: str
    department: Optional[str] = None

    class Config:
        from_attributes = True


class CaseCreate(BaseModel):
    case_number: str
    case_type: str
    jurisdiction: Optional[str] = None
    district: Optional[str] = None
    mandal: Optional[str] = None
    police_station: Optional[str] = None
    revenue_office: Optional[str] = None
    priority: str = "medium"
    source: Optional[str] = None


class CaseOut(BaseModel):
    id: str
    case_number: str
    case_type: str
    jurisdiction: Optional[str]
    district: Optional[str] = None
    mandal: Optional[str] = None
    police_station: Optional[str] = None
    revenue_office: Optional[str] = None
    status: str
    priority: str
    source: Optional[str]
    owner_id: Optional[str]
    legal_hold: bool
    is_active: bool
    disposal_status: str
    is_restricted: bool
    retention_date: Optional[datetime.datetime]
    created_at: datetime.datetime

    class Config:
        from_attributes = True


class OwnerAssignRequest(BaseModel):
    owner_id: str


class RetentionSetRequest(BaseModel):
    retention_date: datetime.datetime


class DisposalRequest(BaseModel):
    disposal_status: str  # pending_disposal | disposed
    reason: Optional[str] = None


class ActiveStatusRequest(BaseModel):
    is_active: bool
    reason: Optional[str] = None


class PartyCreate(BaseModel):
    case_id: str
    matter_id: Optional[str] = None
    party_role: str
    name: str
    contact: Optional[str] = None
    notes: Optional[str] = None


class PartyOut(BaseModel):
    id: str
    case_id: str
    matter_id: Optional[str]
    party_role: str
    name: str
    contact: Optional[str]
    notes: Optional[str]
    created_at: datetime.datetime

    class Config:
        from_attributes = True


class NoteCreate(BaseModel):
    case_id: str
    content: str
    pinned: bool = False


class NoteOut(BaseModel):
    id: str
    case_id: str
    author_name: str
    content: str
    pinned: bool
    created_at: datetime.datetime

    class Config:
        from_attributes = True


class TaskCreate(BaseModel):
    case_id: str
    title: str
    description: Optional[str] = None
    assigned_to_id: Optional[str] = None
    due_date: Optional[datetime.datetime] = None


class TaskUpdate(BaseModel):
    status: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    assigned_to_id: Optional[str] = None
    due_date: Optional[datetime.datetime] = None


class TaskOut(BaseModel):
    id: str
    case_id: str
    title: str
    description: Optional[str]
    status: str
    assigned_to_id: Optional[str]
    assigned_by_id: str
    due_date: Optional[datetime.datetime]
    created_at: datetime.datetime
    completed_at: Optional[datetime.datetime]

    class Config:
        from_attributes = True


class CommentCreate(BaseModel):
    case_id: str
    document_id: Optional[str] = None
    content: str


class CommentOut(BaseModel):
    id: str
    case_id: str
    document_id: Optional[str]
    author_name: str
    content: str
    created_at: datetime.datetime

    class Config:
        from_attributes = True


class NotificationOut(BaseModel):
    id: str
    case_id: Optional[str]
    document_id: Optional[str]
    notif_type: str
    message: str
    is_read: bool
    created_at: datetime.datetime

    class Config:
        from_attributes = True


class DocumentCreate(BaseModel):
    case_id: str
    doc_type: str
    title: str
    origin_type: str  # born_digital | scanned | received_external
    initial_content: str  # placeholder text standing in for uploaded file bytes / template output
    template_id: Optional[str] = None
    matter_id: Optional[str] = None


class DocumentVersionOut(BaseModel):
    id: str
    version_no: int
    sha256_hash: str
    prev_version_hash: Optional[str]
    reason: Optional[str]
    created_by_name: str
    created_at: datetime.datetime
    superseded: bool

    class Config:
        from_attributes = True


class DocumentOut(BaseModel):
    id: str
    doc_ref: str
    case_id: str
    matter_id: Optional[str]
    doc_type: str
    title: str
    origin_type: str
    certified: bool
    status: str
    created_by_id: str
    current_holder_id: Optional[str]
    versions: List[DocumentVersionOut] = []

    class Config:
        from_attributes = True


class TransitionRequest(BaseModel):
    action: str
    reason: Optional[str] = None
    destination: Optional[str] = None  # for transfer actions


class NewVersionRequest(BaseModel):
    content: str  # placeholder for new file bytes
    reason: str


class IntegrityCheckResult(BaseModel):
    document_id: str
    version_id: str
    version_no: int
    recorded_hash: str
    recalculated_hash: str
    verified: bool


class EvidenceCreate(BaseModel):
    case_id: str
    evidence_code: str
    description: str
    seizure_reference: Optional[str] = None
    linked_document_id: Optional[str] = None
    matter_id: Optional[str] = None


class EvidenceOut(BaseModel):
    id: str
    evidence_code: str
    case_id: str
    matter_id: Optional[str]
    description: str
    seizure_reference: Optional[str]
    status: str
    linked_document_id: Optional[str]

    class Config:
        from_attributes = True


class EventOut(BaseModel):
    id: str
    event_type: str
    actor: str
    timestamp: datetime.datetime
    document_id: Optional[str]
    evidence_id: Optional[str]
    from_state: Optional[str]
    to_state: Optional[str]
    source: Optional[str]
    destination: Optional[str]
    details: Optional[str]

    class Config:
        from_attributes = True


class TemplateOut(BaseModel):
    id: str
    name: str
    doc_type: str
    schema_json: Any

    class Config:
        from_attributes = True


class ReadinessOut(BaseModel):
    case_id: str
    total_documents: int
    approved_documents: int
    pending_review: int
    pending_approval_count: int
    integrity_failures: int
    version_conflicts: int
    last_activity: Optional[datetime.datetime]
    completeness_pct: int
    next_required_action: Optional[str]
    checklist: dict


class RestrictedSetRequest(BaseModel):
    is_restricted: bool


class CollaboratorCreate(BaseModel):
    user_id: str
    role_label: str


class CollaboratorOut(BaseModel):
    id: str
    case_id: str
    user_id: str
    user_name: str
    role_label: str
    added_by_name: str
    added_at: datetime.datetime

    class Config:
        from_attributes = True


class AdminReviewOut(BaseModel):
    """Deliberately metadata-only — no content/title field. Admin
    approves the fact that a submission happened, not its substance."""
    id: str
    case_id: str
    case_number: str
    document_id: str
    doc_type: str
    submitted_by_name: str
    status: str
    decision_reason: Optional[str]
    created_at: datetime.datetime
    decided_at: Optional[datetime.datetime]

    class Config:
        from_attributes = True


class AdminReviewDecision(BaseModel):
    status: str  # approved | rejected
    reason: Optional[str] = None


class DisclosureCreate(BaseModel):
    case_id: str
    document_id: str
    reason: Optional[str] = None


class DisclosureOut(BaseModel):
    id: str
    case_id: str
    document_id: str
    doc_ref: str
    doc_type: str
    requested_by_name: str
    reason: Optional[str]
    status: str
    decision_reason: Optional[str]
    created_at: datetime.datetime
    decided_at: Optional[datetime.datetime]

    class Config:
        from_attributes = True


class DisclosedDocumentOut(BaseModel):
    """What the defence side actually receives once a disclosure is
    approved — the one named document's content, nothing else in the
    case."""
    document_id: str
    doc_ref: str
    doc_type: str
    title: str
    content: str
    disclosed_at: datetime.datetime


class CaseFlowStage(BaseModel):
    stage: str
    doc_type: str
    status: str  # not_started | <document status> if a document of this type exists


class CaseFlowOut(BaseModel):
    case_id: str
    stages: List[CaseFlowStage]


class MatterCreate(BaseModel):
    case_id: str
    title: str
    key_question: Optional[str] = None
    status: str = "under_investigation"
    description: Optional[str] = None
    matter_date: Optional[datetime.datetime] = None
    location: Optional[str] = None


class MatterOut(BaseModel):
    id: str
    case_id: str
    title: str
    key_question: Optional[str]
    status: str
    description: Optional[str]
    matter_date: Optional[datetime.datetime]
    location: Optional[str]
    created_by_name: str
    created_at: datetime.datetime
    document_count: int
    evidence_count: int
    witness_count: int

    class Config:
        from_attributes = True


class MatterStatusUpdate(BaseModel):
    status: str


class AssignMatterRequest(BaseModel):
    matter_id: Optional[str] = None  # null clears the assignment


class InboxDocumentOut(BaseModel):
    id: str
    doc_ref: str
    doc_type: str
    title: str
    status: str
    case_id: str
    case_number: str

    class Config:
        from_attributes = True


class DocumentContentOut(BaseModel):
    document_id: str
    version_id: str
    version_no: int
    content: str  # plain text, or a data: URL if the version was a scanned upload
    sha256_hash: str


class DocumentAccessRequestCreate(BaseModel):
    document_id: str
    reason: Optional[str] = None
    requested_mode: str = "view"  # view | edit | append


class DocumentAccessRequestOut(BaseModel):
    id: str
    document_id: str
    doc_ref: str
    doc_type: str
    case_id: str
    requested_by_id: str
    requested_by_name: str
    owner_id: str
    owner_name: str
    reason: Optional[str]
    requested_mode: str
    status: str
    decision_reason: Optional[str]
    granted_mode: Optional[str] = None
    granted_days: Optional[int] = None
    granted_at: Optional[datetime.datetime] = None
    expires_at: Optional[datetime.datetime] = None
    revoked_at: Optional[datetime.datetime] = None
    is_expired: bool = False
    created_at: datetime.datetime
    decided_at: Optional[datetime.datetime]

    class Config:
        from_attributes = True


class AccessDecision(BaseModel):
    status: str  # approved | rejected
    reason: Optional[str] = None
    granted_mode: Optional[str] = None   # defaults to the requested mode if omitted
    granted_days: Optional[int] = None   # required when approving; any integer >= 1


class DocumentLockStatusOut(BaseModel):
    """Tells the frontend, for the current user, whether a document's
    content can be opened right now, and if not, what state any access
    request is in — so the UI can show 'Locked — Request Access',
    'Request pending', or the actual content viewer."""
    document_id: str
    is_owner: bool
    unlocked: bool  # true if content can be fetched right now
    my_request_status: Optional[str]  # None | pending | approved | rejected
    my_granted_mode: Optional[str] = None
    my_expires_at: Optional[datetime.datetime] = None


class AuthorizedOfficerOut(BaseModel):
    """One row in the owner's 'Authorized officers' table for a document."""
    request_id: str
    user_id: str
    user_name: str
    role: str
    mode: str
    granted_at: Optional[datetime.datetime]
    expires_at: Optional[datetime.datetime]
    status: str  # active | expired | revoked
