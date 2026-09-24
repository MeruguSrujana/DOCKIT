"""
Seed script. Creates demo data using the SAME models, services (storage,
events) and password hashing the running application uses — nothing here
is a shortcut or a separate hardcoded path the API doesn't also use.

The demo case is entirely synthetic (per architecture constraint #21):
it is not modeled on any real case, and document contents are placeholder
text, not real records of any kind.

Run with:  python -m app.seed
"""
import datetime

from .database import SessionLocal, Base, engine
from . import models, security, storage
from .events import log_event

Base.metadata.create_all(bind=engine)


ROLES = [
    ("investigating_officer", "Investigating Officer"),
    ("forensic_officer", "Forensic Officer"),
    ("prosecutor", "Prosecutor"),
    ("court_clerk", "Court Clerk"),
    ("admin", "Admin / Case Records Officer"),
    ("cyber_expert", "Cyber Expert"),
]

DEMO_PASSWORD = "Dockit@2026"  # demo only — change immediately in any real deployment

USERS = [
    ("io.sharma", "IO R. Sharma", "investigating_officer", "District Police"),
    ("fo.rao", "Dr. Forensic Officer Rao", "forensic_officer", "Forensic Science Laboratory"),
    ("pp.iyer", "Public Prosecutor Iyer", "prosecutor", "Prosecution Wing"),
    ("cc.das", "Court Clerk Das", "court_clerk", "District Court Registry"),
    ("admin", "Case Records Admin", "admin", "Case Records Section"),
    ("cy.mehta", "Cyber Expert Mehta", "cyber_expert", "Cyber Crime Cell"),
]

TEMPLATES = [
    {
        "name": "Forensic Examination Request",
        "doc_type": "forensic_request",
        "schema_json": [
            {"field": "case_reference", "label": "Case Reference", "type": "text"},
            {"field": "exhibit_description", "label": "Exhibit Description", "type": "text"},
            {"field": "examination_required", "label": "Examination Required", "type": "text"},
            {"field": "requested_by", "label": "Requested By", "type": "text"},
        ],
    },
    {
        "name": "Seizure Memo",
        "doc_type": "seizure_memo",
        "schema_json": [
            {"field": "item_description", "label": "Item Description", "type": "text"},
            {"field": "location_of_seizure", "label": "Location of Seizure", "type": "text"},
            {"field": "witnesses", "label": "Witnesses Present", "type": "text"},
            {"field": "seized_by", "label": "Seized By", "type": "text"},
        ],
    },
    {
        "name": "First Information Report",
        "doc_type": "fir",
        "schema_json": [
            {"field": "complainant_name", "label": "Complainant Name", "type": "text"},
            {"field": "date_time_of_occurrence", "label": "Date & Time of Occurrence", "type": "text"},
            {"field": "place_of_occurrence", "label": "Place of Occurrence", "type": "text"},
            {"field": "offence_details", "label": "Offence Details (Sections)", "type": "text"},
        ],
    },
    {
        "name": "Witness Statement",
        "doc_type": "witness_statement",
        "schema_json": [
            {"field": "witness_name", "label": "Witness Name", "type": "text"},
            {"field": "statement_date", "label": "Date of Statement", "type": "text"},
            {"field": "recorded_by", "label": "Recorded By (Sec 180(3) BNSS)", "type": "text"},
            {"field": "narrative", "label": "Narrative", "type": "text"},
        ],
    },
    {
        "name": "Charge Sheet",
        "doc_type": "charge_sheet",
        "schema_json": [
            {"field": "accused_name", "label": "Accused Name", "type": "text"},
            {"field": "sections_charged", "label": "Sections Charged", "type": "text"},
            {"field": "evidence_summary", "label": "Evidence Summary", "type": "text"},
            {"field": "filed_by", "label": "Filed By (Sec 193 BNSS)", "type": "text"},
        ],
    },
]


def run():
    db = SessionLocal()
    try:
        role_map = {}
        for name, label in ROLES:
            role = db.query(models.Role).filter(models.Role.name == name).first()
            if not role:
                role = models.Role(name=name, label=label)
                db.add(role)
                db.flush()
            role_map[name] = role

        user_map = {}
        for username, full_name, role_name, dept in USERS:
            user = db.query(models.User).filter(models.User.username == username).first()
            if not user:
                user = models.User(
                    username=username, full_name=full_name, department=dept,
                    hashed_password=security.hash_password(DEMO_PASSWORD),
                    role_id=role_map[role_name].id,
                )
                db.add(user)
                db.flush()
            user_map[role_name] = user

        for tpl in TEMPLATES:
            existing = db.query(models.DocumentTemplate).filter(
                models.DocumentTemplate.doc_type == tpl["doc_type"]
            ).first()
            if not existing:
                db.add(models.DocumentTemplate(**tpl))
        db.flush()

        # One synthetic demo case, generic per architecture constraint #21.
        case = db.query(models.Case).filter(models.Case.case_number == "CASE-2026-014").first()
        if not case:
            io_user = user_map["investigating_officer"]
            case = models.Case(
                case_number="CASE-2026-014",
                case_type="crime_against_women",
                jurisdiction="Demo District (synthetic)",
                created_by_id=io_user.id,
            )
            db.add(case)
            db.flush()
            log_event(db, case_id=case.id, actor_id=io_user.id, event_type="created",
                      details="Synthetic demonstration case created for prototype walkthrough.")

            # Seed one FIR document, already registered, via the same
            # storage + versioning path the API uses.
            storage_path, sha = storage.save_content(
                "SYNTHETIC DEMO CONTENT - FIR placeholder text, not a real record.".encode("utf-8")
            )
            fir = models.Document(
                doc_ref=f"DOC-{case.case_number}-001",
                case_id=case.id,
                doc_type="fir",
                title="First Information Report (synthetic demo)",
                origin_type="born_digital",
                status="registered",
                created_by_id=io_user.id,
                current_holder_id=io_user.id,
            )
            db.add(fir)
            db.flush()
            version = models.DocumentVersion(
                document_id=fir.id, version_no=1, storage_path=storage_path,
                sha256_hash=sha, prev_version_hash=None,
                reason="Initial creation", created_by_id=io_user.id,
            )
            db.add(version)
            db.flush()
            log_event(db, case_id=case.id, document_id=fir.id, actor_id=io_user.id,
                      event_type="created", to_state="draft", details="FIR created, version 1")
            log_event(db, case_id=case.id, document_id=fir.id, actor_id=io_user.id,
                      event_type="registered", from_state="draft", to_state="registered",
                      details="FIR registered")

            admin_user = user_map["admin"]
            fir_review = models.AdminReview(
                document_id=fir.id, case_id=case.id, doc_type=fir.doc_type,
                submitted_by_id=io_user.id, status="approved",
                decided_by_id=admin_user.id, decided_at=fir.created_at,
            )
            db.add(fir_review)

            cy_user = user_map["cyber_expert"]
            db.add(models.CaseCollaborator(
                case_id=case.id, user_id=cy_user.id, role_label="Cyber Expert",
                added_by_id=admin_user.id,
            ))

            pp_user = user_map["prosecutor"]
            db.add(models.DisclosureRequest(
                case_id=case.id, document_id=fir.id, requested_by_id=pp_user.id,
                reason="SYNTHETIC DEMO — defence advocate entitled to FIR copy under Sec 230 BNSS",
            ))

            matter = models.CaseMatter(
                case_id=case.id, title="Unauthorized entry into government warehouse",
                key_question="Was the accused present at the warehouse at the time of the theft?",
                status="under_investigation",
                description="SYNTHETIC DEMO — groups every document/evidence tied to this one incident location, "
                            "instead of a flat per-case document list.",
                location="Main St. Godown", created_by_id=io_user.id,
            )
            db.add(matter)
            db.flush()
            fir.matter_id = matter.id

            EVIDENCE_ITEMS = [
                ("Broken padlock recovered from warehouse gate", "SEIZ-DEMO-001"),
                ("CCTV footage extract — 2 minute clip, gate camera", "SEIZ-DEMO-002"),
                ("Fingerprint lift from gate handle", "SEIZ-DEMO-003"),
                ("Inventory ledger — missing item list", "SEIZ-DEMO-004"),
                ("Footwear impression cast from warehouse floor", "SEIZ-DEMO-005"),
            ]
            for i, (desc, seiz_ref) in enumerate(EVIDENCE_ITEMS, start=1):
                db.add(models.Evidence(
                    evidence_code=f"E-{case.case_number}-{i:03d}",
                    case_id=case.id, matter_id=matter.id,
                    description=f"SYNTHETIC DEMO — {desc}",
                    seizure_reference=seiz_ref, created_by_id=io_user.id,
                ))

            case.owner_id = io_user.id
            case.priority = "high"
            case.source = "e_fir"

            db.add(models.CaseParty(
                case_id=case.id, party_role="complainant", name="Synthetic Complainant (demo)",
                contact="N/A (synthetic)", created_by_id=io_user.id,
            ))
            db.add(models.CaseParty(
                case_id=case.id, matter_id=matter.id, party_role="witness",
                name="Synthetic Witness — Night Watchman (demo)", created_by_id=io_user.id,
            ))
            db.add(models.CaseParty(
                case_id=case.id, matter_id=matter.id, party_role="witness",
                name="Synthetic Witness — Neighboring Shopkeeper (demo)", created_by_id=io_user.id,
            ))
            db.add(models.CaseNote(
                case_id=case.id, author_id=io_user.id, pinned=True,
                content="SYNTHETIC DEMO NOTE - initial case brief, not a real record.",
            ))
            fo_user = user_map["forensic_officer"]
            task = models.Task(
                case_id=case.id, title="Submit forensic examination request",
                description="SYNTHETIC DEMO TASK - not a real record.",
                assigned_to_id=fo_user.id, assigned_by_id=io_user.id,
            )
            db.add(task)
            db.flush()
            log_event(db, case_id=case.id, actor_id=io_user.id, event_type="task_created",
                      details=f"Task '{task.title}' created")
            db.add(models.Notification(
                user_id=fo_user.id, case_id=case.id, notif_type="task_assigned",
                message=f"You were assigned task '{task.title}' on case {case.case_number}",
            ))

        seed_closed_case(db, user_map)
        seed_ongoing_case(db, user_map)

        db.commit()
        print("Seed complete.")
        print(f"Demo login (all users): password = {DEMO_PASSWORD}")
        for username, full_name, role_name, _ in USERS:
            print(f"  username={username:12s} role={role_name}")
    finally:
        db.close()


def _make_doc(db, case, matter, doc_type, title, content_text, status, owner, holder=None, reason="Initial creation"):
    """Same create-document + first-version path the API uses."""
    storage_path, sha = storage.save_content(content_text.encode("utf-8"))
    count = db.query(models.Document).filter(models.Document.case_id == case.id).count()
    doc = models.Document(
        doc_ref=f"DOC-{case.case_number}-{count + 1:03d}",
        case_id=case.id, matter_id=matter.id if matter else None,
        doc_type=doc_type, title=title, origin_type="born_digital",
        status=status, created_by_id=owner.id, current_holder_id=(holder or owner).id,
    )
    db.add(doc)
    db.flush()
    version = models.DocumentVersion(
        document_id=doc.id, version_no=1, storage_path=storage_path,
        sha256_hash=sha, prev_version_hash=None, reason=reason, created_by_id=owner.id,
    )
    db.add(version)
    db.flush()
    log_event(db, case_id=case.id, document_id=doc.id, actor_id=owner.id,
              event_type="created", to_state="draft", details=f"{title} created, version 1")
    if status != "draft":
        log_event(db, case_id=case.id, document_id=doc.id, actor_id=owner.id,
                  event_type="registered", from_state="draft", to_state=status,
                  details=f"{title} moved to {status}")
    return doc


def seed_closed_case(db, user_map):
    """CASE-2026-021 — SYNTHETIC demo modeled on a common cyber-fraud
    pattern ('digital arrest' courier scam), not a real case. Closed /
    fully approved, so the readiness view shows a completed case."""
    if db.query(models.Case).filter(models.Case.case_number == "CASE-2026-021").first():
        return
    io_user = user_map["investigating_officer"]
    fo_user = user_map["forensic_officer"]
    cy_user = user_map["cyber_expert"]
    admin_user = user_map["admin"]

    case = models.Case(
        case_number="CASE-2026-021", case_type="cyber_crime",
        district="Hyderabad", mandal="Charminar", police_station="Charminar I Town PS",
        jurisdiction="Charminar I Town PS, Charminar, Hyderabad",
        status="closed", priority="high", source="e_fir",
        created_by_id=io_user.id, owner_id=io_user.id,
    )
    db.add(case)
    db.flush()
    log_event(db, case_id=case.id, actor_id=io_user.id, event_type="created",
              details="SYNTHETIC DEMO — modeled on a common 'digital arrest' courier-scam pattern, not a real case.")

    matter1 = models.CaseMatter(
        case_id=case.id, title="Fake courier call and video-call coercion",
        key_question="Was the complainant deceived into transferring funds under threat of fabricated legal action?",
        status="closed", location="Complainant's residence, Hyderabad",
        description="SYNTHETIC DEMO — a caller posing as a courier/CBI officer kept the complainant on a video call "
                    "and coerced UPI transfers over several hours.",
        created_by_id=io_user.id,
    )
    matter2 = models.CaseMatter(
        case_id=case.id, title="Money trail across mule accounts",
        key_question="Which accounts received the transferred funds, and who controls them?",
        status="closed", location="N/A — digital trail",
        description="SYNTHETIC DEMO — bank layering and SIM records used to trace the funds to the accused.",
        created_by_id=io_user.id,
    )
    db.add_all([matter1, matter2])
    db.flush()

    fir = _make_doc(db, case, matter1, "fir", "First Information Report (synthetic demo)",
                     "SYNTHETIC DEMO CONTENT — FIR: complainant reports fraudulent inducement to transfer funds "
                     "over a video call impersonating a courier/CBI official.", "approved", io_user)
    witness = _make_doc(db, case, matter1, "witness_statement", "Witness Statement — Complainant (synthetic demo)",
                         "SYNTHETIC DEMO CONTENT — complainant's statement describing the call, the threats made, "
                         "and each UPI transfer.", "approved", io_user)
    seizure = _make_doc(db, case, matter2, "seizure_memo", "Seizure Memo — Phones and SIM cards (synthetic demo)",
                         "SYNTHETIC DEMO CONTENT — seizure of two mobile phones and three SIM cards from the "
                         "accused at the time of arrest.", "approved", io_user)
    forensic = _make_doc(db, case, matter2, "forensic_report", "Forensic Report — Device Analysis (synthetic demo)",
                          "SYNTHETIC DEMO CONTENT — extraction of call logs, UPI app data and chat history from "
                          "the seized devices, cross-referenced against the bank layering trail.", "approved", fo_user)
    charge_sheet = _make_doc(db, case, matter2, "charge_sheet", "Charge Sheet (synthetic demo)",
                              "SYNTHETIC DEMO CONTENT — charges filed against two accused under fraud and "
                              "impersonation provisions, evidence summary attached.", "approved", io_user)
    court_filing = _make_doc(db, case, matter2, "court_filing", "Court Filing — Judgment (synthetic demo)",
                              "SYNTHETIC DEMO CONTENT — trial concluded with conviction of both accused; "
                              "case disposed and closed.", "approved", io_user)

    for d in (fir, witness, seizure, forensic, charge_sheet, court_filing):
        db.add(models.AdminReview(
            document_id=d.id, case_id=case.id, doc_type=d.doc_type,
            submitted_by_id=d.created_by_id, status="approved",
            decided_by_id=admin_user.id, decided_at=d.created_at,
        ))

    EVIDENCE = [
        ("Seized mobile phone — accused #1 (synthetic demo)", "archived"),
        ("SIM cards recovered at arrest (synthetic demo)", "archived"),
        ("Bank statement extract — mule account layering (synthetic demo)", "archived"),
        ("Call-detail records, three linked numbers (synthetic demo)", "archived"),
    ]
    for i, (desc, ev_status) in enumerate(EVIDENCE, start=1):
        db.add(models.Evidence(
            evidence_code=f"E-{case.case_number}-{i:03d}", case_id=case.id, matter_id=matter2.id,
            description=desc, seizure_reference=f"SEIZ-{case.case_number}-{i:03d}",
            status=ev_status, linked_document_id=seizure.id if i <= 2 else None,
            created_by_id=io_user.id,
        ))

    db.add(models.CaseParty(case_id=case.id, party_role="complainant",
                             name="Synthetic Complainant — Senior Citizen (demo)", created_by_id=io_user.id))
    db.add(models.CaseParty(case_id=case.id, matter_id=matter2.id, party_role="accused",
                             name="Synthetic Accused #1 (demo)", created_by_id=io_user.id))
    db.add(models.CaseParty(case_id=case.id, matter_id=matter2.id, party_role="accused",
                             name="Synthetic Accused #2 (demo)", created_by_id=io_user.id))
    db.add(models.CaseCollaborator(case_id=case.id, user_id=cy_user.id, role_label="Cyber Expert",
                                    added_by_id=admin_user.id))

    # One EXPIRED access grant on the forensic report, so the owner's
    # Authorized Officers table has an expired row to show.
    now = datetime.datetime.utcnow()
    expired_req = models.DocumentAccessRequest(
        document_id=forensic.id, case_id=case.id, requested_by_id=io_user.id, owner_id=fo_user.id,
        reason="SYNTHETIC DEMO — reviewed forensic findings ahead of the charge sheet.",
        requested_mode="edit", status="approved",
        granted_mode="edit", granted_days=7,
        granted_at=now - datetime.timedelta(days=20),
        expires_at=now - datetime.timedelta(days=13),
        decided_at=now - datetime.timedelta(days=20),
        created_at=now - datetime.timedelta(days=21),
    )
    db.add(expired_req)


def seed_ongoing_case(db, user_map):
    """CASE-2026-022 — SYNTHETIC demo modeled on a common hit-and-run
    pattern, not a real case. Active / partially complete, with a
    pending access request and a live grant, so the countdown and
    approval flow have something real to show."""
    if db.query(models.Case).filter(models.Case.case_number == "CASE-2026-022").first():
        return
    io_user = user_map["investigating_officer"]
    fo_user = user_map["forensic_officer"]

    case = models.Case(
        case_number="CASE-2026-022", case_type="road_accident",
        district="Medchal-Malkajgiri", mandal="Malkajgiri", police_station="Malkajgiri I Town PS",
        jurisdiction="Malkajgiri I Town PS, Malkajgiri, Medchal-Malkajgiri",
        status="active", priority="high", source="walk_in",
        created_by_id=io_user.id, owner_id=io_user.id,
    )
    db.add(case)
    db.flush()
    log_event(db, case_id=case.id, actor_id=io_user.id, event_type="created",
              details="SYNTHETIC DEMO — modeled on a common night-time hit-and-run pattern, not a real case.")

    matter1 = models.CaseMatter(
        case_id=case.id, title="Hit-and-run at ORR exit",
        key_question="What vehicle struck the complainant's two-wheeler, and did it stop?",
        status="evidence_collection", location="Outer Ring Road exit ramp",
        description="SYNTHETIC DEMO — a two-wheeler rider was struck at night by a fast-moving car that did not stop.",
        created_by_id=io_user.id,
    )
    matter2 = models.CaseMatter(
        case_id=case.id, title="Vehicle and owner identification",
        key_question="Whose vehicle matches the partial plate and paint transfer?",
        status="under_investigation", location="N/A — vehicle trace",
        description="SYNTHETIC DEMO — tracing the vehicle from a partial number plate and paint chip analysis.",
        created_by_id=io_user.id,
    )
    db.add_all([matter1, matter2])
    db.flush()

    fir = _make_doc(db, case, matter1, "fir", "First Information Report (synthetic demo)",
                     "SYNTHETIC DEMO CONTENT — FIR: complainant's family reports a hit-and-run on the ORR exit "
                     "ramp; struck by an unidentified car that fled the scene.", "approved", io_user)
    witness = _make_doc(db, case, matter1, "witness_statement", "Witness Statement — Passing Motorist (synthetic demo)",
                         "SYNTHETIC DEMO CONTENT — eyewitness describes a dark-colored sedan leaving the scene at "
                         "high speed, partial plate ending in 4471.", "approved", io_user)
    seizure = _make_doc(db, case, matter1, "seizure_memo", "Seizure Memo — Paint Chips (synthetic demo)",
                         "SYNTHETIC DEMO CONTENT — paint chips recovered from the road surface at the point of "
                         "impact, sealed for forensic comparison.", "under_review", io_user)
    forensic_req = _make_doc(db, case, matter2, "forensic_request", "Forensic Examination Request — Paint Analysis (synthetic demo)",
                              "SYNTHETIC DEMO CONTENT — requesting paint composition and make/model comparison "
                              "against the recovered chips.", "transferred", io_user, holder=fo_user)

    for d in (fir, witness):
        db.add(models.AdminReview(
            document_id=d.id, case_id=case.id, doc_type=d.doc_type,
            submitted_by_id=d.created_by_id, status="approved",
            decided_by_id=user_map["admin"].id, decided_at=d.created_at,
        ))
    db.add(models.AdminReview(
        document_id=seizure.id, case_id=case.id, doc_type=seizure.doc_type,
        submitted_by_id=seizure.created_by_id, status="pending",
    ))

    db.add(models.Evidence(evidence_code=f"E-{case.case_number}-001", case_id=case.id, matter_id=matter1.id,
                            description="Paint chips from point of impact (synthetic demo)",
                            seizure_reference=f"SEIZ-{case.case_number}-001", status="transferred",
                            linked_document_id=seizure.id, created_by_id=io_user.id))
    db.add(models.Evidence(evidence_code=f"E-{case.case_number}-002", case_id=case.id, matter_id=matter1.id,
                            description="CCTV extract, toll plaza camera (synthetic demo)",
                            seizure_reference=f"SEIZ-{case.case_number}-002", status="received",
                            created_by_id=io_user.id))
    db.add(models.Evidence(evidence_code=f"E-{case.case_number}-003", case_id=case.id, matter_id=matter1.id,
                            description="Dashcam clip from passing truck (synthetic demo)",
                            seizure_reference=f"SEIZ-{case.case_number}-003", status="collected",
                            created_by_id=io_user.id))

    db.add(models.CaseParty(case_id=case.id, party_role="complainant",
                             name="Synthetic Complainant — Rider's Family Member (demo)", created_by_id=io_user.id))
    db.add(models.CaseParty(case_id=case.id, matter_id=matter1.id, party_role="witness",
                             name="Synthetic Witness — Passing Motorist (demo)", created_by_id=io_user.id))

    task = models.Task(
        case_id=case.id, title="Trace vehicle owner from partial number plate",
        description="SYNTHETIC DEMO TASK — cross-check partial plate 4471 against RTA records for dark sedans.",
        assigned_to_id=io_user.id, assigned_by_id=io_user.id,
    )
    db.add(task)
    db.flush()
    log_event(db, case_id=case.id, actor_id=io_user.id, event_type="task_created",
              details=f"Task '{task.title}' created")
    db.add(models.CaseNote(case_id=case.id, author_id=io_user.id, pinned=True,
                            content="SYNTHETIC DEMO NOTE — priority is the paint-chip lab comparison; owner "
                                    "expects vehicle make/model match within the week."))

    now = datetime.datetime.utcnow()

    # (1) PENDING request: fo.rao wants Edit access to the forensic
    # examination request document, waiting on io.sharma.
    db.add(models.DocumentAccessRequest(
        document_id=forensic_req.id, case_id=case.id, requested_by_id=fo_user.id, owner_id=io_user.id,
        reason="SYNTHETIC DEMO — need to add examination findings once the lab comparison is complete.",
        requested_mode="edit", status="pending",
        created_at=now - datetime.timedelta(hours=6),
    ))

    # (2) ACTIVE grant: fo.rao has View access to the witness statement,
    # several days remaining, so the countdown displays live.
    db.add(models.DocumentAccessRequest(
        document_id=witness.id, case_id=case.id, requested_by_id=fo_user.id, owner_id=io_user.id,
        reason="SYNTHETIC DEMO — cross-checking the witness's plate description against the paint match.",
        requested_mode="view", status="approved",
        granted_mode="view", granted_days=7,
        granted_at=now - datetime.timedelta(days=2),
        expires_at=now + datetime.timedelta(days=5),
        decided_at=now - datetime.timedelta(days=2),
        created_at=now - datetime.timedelta(days=2, hours=1),
    ))

    # (3) An older EXPIRED grant on the FIR, for the Authorized Officers
    # table's expired-row state.
    db.add(models.DocumentAccessRequest(
        document_id=fir.id, case_id=case.id, requested_by_id=fo_user.id, owner_id=io_user.id,
        reason="SYNTHETIC DEMO — initial FIR review.",
        requested_mode="view", status="approved",
        granted_mode="view", granted_days=1,
        granted_at=now - datetime.timedelta(days=10),
        expires_at=now - datetime.timedelta(days=9),
        decided_at=now - datetime.timedelta(days=10),
        created_at=now - datetime.timedelta(days=10, hours=1),
    ))


if __name__ == "__main__":
    run()
