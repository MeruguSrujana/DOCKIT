import datetime
import uuid
from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, ForeignKey, Text, JSON
)
from sqlalchemy.orm import relationship
from .database import Base


def _id():
    return str(uuid.uuid4())


class Role(Base):
    """One of the 8 architecture entities. Fixed vocabulary of roles."""
    __tablename__ = "roles"
    id = Column(String, primary_key=True, default=_id)
    name = Column(String, unique=True, nullable=False)  # e.g. investigating_officer
    label = Column(String, nullable=False)               # e.g. Investigating Officer

    users = relationship("User", back_populates="role")


class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=_id)
    username = Column(String, unique=True, nullable=False, index=True)
    full_name = Column(String, nullable=False)
    department = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    role_id = Column(String, ForeignKey("roles.id"), nullable=False)
    is_active = Column(Boolean, default=True)

    role = relationship("Role", back_populates="users")


class DocumentTemplate(Base):
    """Structured-creation templates (Innovation #2). schema_json defines
    the fields a user fills to generate a document deterministically —
    no generative drafting, per architecture constraint on AI."""
    __tablename__ = "document_templates"
    id = Column(String, primary_key=True, default=_id)
    name = Column(String, nullable=False)          # e.g. "Forensic Examination Request"
    doc_type = Column(String, nullable=False)       # e.g. "forensic_request"
    schema_json = Column(JSON, nullable=False)       # [{ "field": "...", "label": "...", "type": "..." }]
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class Case(Base):
    __tablename__ = "cases"
    id = Column(String, primary_key=True, default=_id)
    case_number = Column(String, unique=True, nullable=False)   # CASE-2026-014
    case_type = Column(String, nullable=False)                   # e.g. "crime_against_women"
    jurisdiction = Column(String, nullable=True)
    district = Column(String, nullable=True)
    mandal = Column(String, nullable=True)
    police_station = Column(String, nullable=True)
    revenue_office = Column(String, nullable=True)
    status = Column(String, nullable=False, default="active")    # active | closed | archived
    priority = Column(String, nullable=False, default="medium")  # low | medium | high | critical
    source = Column(String, nullable=True)                       # walk_in | e_fir | zero_fir | referral | other
    owner_id = Column(String, ForeignKey("users.id"), nullable=True)
    legal_hold = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    disposal_status = Column(String, nullable=False, default="active")  # active | pending_disposal | disposed
    is_restricted = Column(Boolean, default=False)  # sensitive case: content visible only to collaborators + Admin's flow view
    created_by_id = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    retention_date = Column(DateTime, nullable=True)

    created_by = relationship("User", foreign_keys=[created_by_id])
    owner = relationship("User", foreign_keys=[owner_id])
    documents = relationship("Document", back_populates="case", cascade="all, delete-orphan")
    evidence_items = relationship("Evidence", back_populates="case", cascade="all, delete-orphan")
    events = relationship("Event", back_populates="case", cascade="all, delete-orphan")
    parties = relationship("CaseParty", back_populates="case", cascade="all, delete-orphan")
    notes = relationship("CaseNote", back_populates="case", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="case", cascade="all, delete-orphan")


class Document(Base):
    __tablename__ = "documents"
    id = Column(String, primary_key=True, default=_id)
    doc_ref = Column(String, unique=True, nullable=False)   # DOC-<case short>-<seq>, the "passport" ID
    case_id = Column(String, ForeignKey("cases.id"), nullable=False)
    matter_id = Column(String, ForeignKey("case_matters.id"), nullable=True)
    doc_type = Column(String, nullable=False)   # fir | witness_statement | forensic_report | charge_sheet | ...
    title = Column(String, nullable=False)
    origin_type = Column(String, nullable=False)  # born_digital | scanned | received_external
    template_id = Column(String, ForeignKey("document_templates.id"), nullable=True)
    certified = Column(Boolean, default=False)
    status = Column(String, nullable=False, default="draft")
    # draft -> registered -> under_review -> approved -> transferred -> received -> archived
    current_holder_id = Column(String, ForeignKey("users.id"), nullable=True)
    created_by_id = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    case = relationship("Case", back_populates="documents")
    matter = relationship("CaseMatter")
    created_by = relationship("User", foreign_keys=[created_by_id])
    current_holder = relationship("User", foreign_keys=[current_holder_id])
    versions = relationship("DocumentVersion", back_populates="document",
                             cascade="all, delete-orphan", order_by="DocumentVersion.version_no")


class DocumentVersion(Base):
    __tablename__ = "document_versions"
    id = Column(String, primary_key=True, default=_id)
    document_id = Column(String, ForeignKey("documents.id"), nullable=False)
    version_no = Column(Integer, nullable=False)
    storage_path = Column(String, nullable=False)   # pointer into object storage, not the file itself
    sha256_hash = Column(String, nullable=False)
    prev_version_hash = Column(String, nullable=True)
    reason = Column(String, nullable=True)
    created_by_id = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    superseded = Column(Boolean, default=False)

    document = relationship("Document", back_populates="versions")
    created_by = relationship("User")

    @property
    def created_by_name(self) -> str:
        return self.created_by.full_name if self.created_by else ""


class CaseMatter(Base):
    """Procedural/event-based grouping within a case — DOCKIT's answer to
    'documents dumped in a flat pile'. A case can span several distinct
    matters (e.g. a land-acquisition case has one matter per parcel/date;
    a theft case has one matter per location of evidence). Every
    document, evidence item, and party tied to the same real-world
    event/incident is grouped here, so investigators see 'everything
    about this incident' as one unit instead of hunting a flat list."""
    __tablename__ = "case_matters"
    id = Column(String, primary_key=True, default=_id)
    case_id = Column(String, ForeignKey("cases.id"), nullable=False)
    title = Column(String, nullable=False)
    key_question = Column(String, nullable=True)  # e.g. "Was the accused present at the time?"
    status = Column(String, nullable=False, default="under_investigation")
    # under_investigation | evidence_collection | pending_review | closed
    description = Column(String, nullable=True)
    matter_date = Column(DateTime, nullable=True)
    location = Column(String, nullable=True)
    created_by_id = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    case = relationship("Case")
    created_by = relationship("User")


class Evidence(Base):
    """Links physical custody to its digital documentary trail."""
    __tablename__ = "evidence"
    id = Column(String, primary_key=True, default=_id)
    evidence_code = Column(String, unique=True, nullable=False)  # E-001
    case_id = Column(String, ForeignKey("cases.id"), nullable=False)
    matter_id = Column(String, ForeignKey("case_matters.id"), nullable=True)
    seizure_reference = Column(String, nullable=True)
    description = Column(String, nullable=False)
    linked_document_id = Column(String, ForeignKey("documents.id"), nullable=True)
    status = Column(String, nullable=False, default="collected")
    # collected -> sealed -> transferred -> received -> examined -> report_generated -> used -> archived
    created_by_id = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    case = relationship("Case", back_populates="evidence_items")
    matter = relationship("CaseMatter")
    linked_document = relationship("Document")
    created_by = relationship("User")


class Event(Base):
    """Single polymorphic, append-only ledger. Every workflow, transfer,
    custody, approval, integrity, and adapter action is one row here.
    This table is the sole source of the provenance timeline, the audit
    trail, and the documentary-readiness computation — nothing above it
    is allowed to fabricate history that isn't a row in this table."""
    __tablename__ = "events"
    id = Column(String, primary_key=True, default=_id)
    case_id = Column(String, ForeignKey("cases.id"), nullable=False)
    document_id = Column(String, ForeignKey("documents.id"), nullable=True)
    evidence_id = Column(String, ForeignKey("evidence.id"), nullable=True)
    event_type = Column(String, nullable=False)
    # created | registered | reviewed | approved | rejected | transferred |
    # received | version_created | integrity_check | integrity_failure |
    # permission_denied | archived | adapter_inbound | adapter_outbound
    actor_id = Column(String, ForeignKey("users.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    from_state = Column(String, nullable=True)
    to_state = Column(String, nullable=True)
    source = Column(String, nullable=True)
    destination = Column(String, nullable=True)
    details = Column(Text, nullable=True)

    case = relationship("Case", back_populates="events")
    document = relationship("Document")
    evidence = relationship("Evidence")
    actor = relationship("User")


class CaseParty(Base):
    """A person or entity attached to a case (complainant, accused, witness,
    advocate, etc.) — captured during Initiate & Collect."""
    __tablename__ = "case_parties"
    id = Column(String, primary_key=True, default=_id)
    case_id = Column(String, ForeignKey("cases.id"), nullable=False)
    matter_id = Column(String, ForeignKey("case_matters.id"), nullable=True)
    party_role = Column(String, nullable=False)   # complainant | accused | witness | advocate | other
    name = Column(String, nullable=False)
    contact = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    created_by_id = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    case = relationship("Case", back_populates="parties")
    matter = relationship("CaseMatter")
    created_by = relationship("User")


class CaseNote(Base):
    """Free-text investigative note on a case, distinct from the immutable
    event ledger — notes can be about context/observations, not just state
    transitions."""
    __tablename__ = "case_notes"
    id = Column(String, primary_key=True, default=_id)
    case_id = Column(String, ForeignKey("cases.id"), nullable=False)
    author_id = Column(String, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    pinned = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    case = relationship("Case", back_populates="notes")
    author = relationship("User")


class Task(Base):
    """An actionable follow-up assigned to a role/user on a case — the
    Manage & Review stage's work-tracking unit."""
    __tablename__ = "tasks"
    id = Column(String, primary_key=True, default=_id)
    case_id = Column(String, ForeignKey("cases.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String, nullable=False, default="pending")  # pending | in_progress | done | cancelled
    assigned_to_id = Column(String, ForeignKey("users.id"), nullable=True)
    assigned_by_id = Column(String, ForeignKey("users.id"), nullable=False)
    due_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    case = relationship("Case", back_populates="tasks")
    assigned_to = relationship("User", foreign_keys=[assigned_to_id])
    assigned_by = relationship("User", foreign_keys=[assigned_by_id])


class Comment(Base):
    """A discussion comment threaded on a case or a specific document,
    for review/collaboration — separate from the immutable event ledger."""
    __tablename__ = "comments"
    id = Column(String, primary_key=True, default=_id)
    case_id = Column(String, ForeignKey("cases.id"), nullable=False)
    document_id = Column(String, ForeignKey("documents.id"), nullable=True)
    author_id = Column(String, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    case = relationship("Case")
    document = relationship("Document")
    author = relationship("User")


class Notification(Base):
    """In-app notification for a user — the Deliver & Execute stage's
    delivery record. Distinct from Event: an Event is what happened to a
    case/document; a Notification is who was told about it."""
    __tablename__ = "notifications"
    id = Column(String, primary_key=True, default=_id)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    case_id = Column(String, ForeignKey("cases.id"), nullable=True)
    document_id = Column(String, ForeignKey("documents.id"), nullable=True)
    notif_type = Column(String, nullable=False)   # task_assigned | document_transferred | review_required | ...
    message = Column(String, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User")
    case = relationship("Case")
    document = relationship("Document")


class CaseCollaborator(Base):
    """A person added to a specific case's access list by Admin, outside
    the 4 default roles (e.g. a cyber-cell specialist, translator, or an
    officer from another department). Only Admin can add/remove these —
    this is per-case access, not a global role. Once a case is marked
    is_restricted, only its collaborators (plus the case owner/creator
    and Admin) may open it."""
    __tablename__ = "case_collaborators"
    id = Column(String, primary_key=True, default=_id)
    case_id = Column(String, ForeignKey("cases.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    role_label = Column(String, nullable=False)  # free text, e.g. "Cyber Expert", "Translator"
    added_by_id = Column(String, ForeignKey("users.id"), nullable=False)
    added_at = Column(DateTime, default=datetime.datetime.utcnow)

    case = relationship("Case")
    user = relationship("User", foreign_keys=[user_id])
    added_by = relationship("User", foreign_keys=[added_by_id])


class AdminReview(Base):
    """Every document submission passes through this queue. Admin sees
    ONLY metadata here (doc type, who submitted it, when) — never the
    document's content — and approves or rejects the submission as a
    procedural checkpoint. This is intentionally separate from the
    document's own workflow state (draft/registered/approved/...): that
    workflow is content-bearing and role-specific; this is Admin's
    content-blind procedural gate on top of it."""
    __tablename__ = "admin_reviews"
    id = Column(String, primary_key=True, default=_id)
    document_id = Column(String, ForeignKey("documents.id"), nullable=False)
    case_id = Column(String, ForeignKey("cases.id"), nullable=False)
    doc_type = Column(String, nullable=False)
    submitted_by_id = Column(String, ForeignKey("users.id"), nullable=False)
    status = Column(String, nullable=False, default="pending")  # pending | approved | rejected
    decision_reason = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    decided_at = Column(DateTime, nullable=True)
    decided_by_id = Column(String, ForeignKey("users.id"), nullable=True)

    document = relationship("Document")
    case = relationship("Case")
    submitted_by = relationship("User", foreign_keys=[submitted_by_id])
    decided_by = relationship("User", foreign_keys=[decided_by_id])


class DocumentAccessRequest(Base):
    """The lock on a document's content between the case's own authorized
    officials. A document's OWNER is whoever created it — e.g. a
    Forensic Officer who uploads a forensic report owns it. Every other
    authorized official (including the Investigating Officer, the case
    owner, and Admin) sees the document listed but its content stays
    locked until the OWNER — not Admin — approves a request. This is
    deliberately separate from the procedural transfer/custody workflow
    (transfer → acknowledge_receipt still moves who holds the document
    procedurally) and separate from DisclosureRequest (which governs
    release to the defence side, not to fellow case officials)."""
    __tablename__ = "document_access_requests"
    id = Column(String, primary_key=True, default=_id)
    document_id = Column(String, ForeignKey("documents.id"), nullable=False)
    case_id = Column(String, ForeignKey("cases.id"), nullable=False)
    requested_by_id = Column(String, ForeignKey("users.id"), nullable=False)
    owner_id = Column(String, ForeignKey("users.id"), nullable=False)
    reason = Column(String, nullable=True)
    requested_mode = Column(String, nullable=False, default="view")  # view | edit | append
    status = Column(String, nullable=False, default="pending")  # pending | approved | rejected
    decision_reason = Column(String, nullable=True)
    granted_mode = Column(String, nullable=True)       # view | edit | append, set on approval
    granted_days = Column(Integer, nullable=True)       # number of days the owner granted
    granted_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    decided_at = Column(DateTime, nullable=True)

    document = relationship("Document")
    case = relationship("Case")
    requested_by = relationship("User", foreign_keys=[requested_by_id])
    owner = relationship("User", foreign_keys=[owner_id])


class DisclosureRequest(Base):
    """The ONLY path by which any document reaches the defence side
    (accused / defence advocate). Defence has zero access by default —
    Sec 230/231 BNSS entitles the accused (and victim's advocate) to
    specific documents, not the whole case file. A Prosecutor or Court
    Clerk raises the request naming exactly which document; only Admin
    may approve or reject it. Approval does not grant browsing — it
    releases that one named document."""
    __tablename__ = "disclosure_requests"
    id = Column(String, primary_key=True, default=_id)
    case_id = Column(String, ForeignKey("cases.id"), nullable=False)
    document_id = Column(String, ForeignKey("documents.id"), nullable=False)
    requested_by_id = Column(String, ForeignKey("users.id"), nullable=False)
    reason = Column(String, nullable=True)
    status = Column(String, nullable=False, default="pending")  # pending | approved | rejected
    decision_reason = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    decided_at = Column(DateTime, nullable=True)
    decided_by_id = Column(String, ForeignKey("users.id"), nullable=True)

    case = relationship("Case")
    document = relationship("Document")
    requested_by = relationship("User", foreign_keys=[requested_by_id])
    decided_by = relationship("User", foreign_keys=[decided_by_id])
