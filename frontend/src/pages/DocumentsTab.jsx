import { useEffect, useState, useRef } from "react";
import { api } from "../api";
import { useAuth } from "../AuthContext";

/*
 * UI POLICY MAP
 * Backend policy.py remains the final authority.
 */
const ROLE_ACTIONS = {
  investigating_officer: {
    draft: [["register", "Register"]],
    registered: [["submit_for_review", "Submit for Review"]],
    approved: [["transfer", "Transfer to FO"]],
    received: [["submit_for_review", "Further Investigation"]],
  },

  forensic_officer: {
    transferred: [["acknowledge_receipt", "Receive Document"]],
    received: [["submit_for_review", "Submit Report"]],
    under_review: [
      ["approve", "Approve"],
      ["reject", "Reject"],
    ],
    approved: [["transfer", "Transfer to Prosecutor"]],
  },

  prosecutor: {
    transferred: [["acknowledge_receipt", "Receive"]],
    under_review: [
      ["approve", "Approve"],
      ["reject", "Reject"],
    ],
    approved: [["transfer", "Transfer to Court"]],
  },

  court_clerk: {
    transferred: [["acknowledge_receipt", "Receive"]],
    received: [["archive", "Archive"]],
  },

  admin: {
    draft: [["register", "Register"]],
    registered: [["submit_for_review", "Submit"]],
    under_review: [
      ["approve", "Approve"],
      ["reject", "Reject"],
    ],
    approved: [
      ["transfer", "Transfer"],
      ["archive", "Archive"],
    ],
    transferred: [["acknowledge_receipt", "Receive"]],
    received: [["archive", "Archive"]],
  },
};

const DOC_TYPES = [
  "fir",
  "witness_statement",
  "forensic_report",
  "charge_sheet",
  "forensic_request",
  "seizure_memo",
  "court_filing",
];

const CARDS = [
  { doc_type: "fir", label: "FIR" },
  { doc_type: "witness_statement", label: "Witness Statement" },
  { doc_type: "forensic_report", label: "Forensic Report" },
  { doc_type: "forensic_request", label: "Forensic Request" },
  { doc_type: "charge_sheet", label: "Charge Sheet" },
  { doc_type: "seizure_memo", label: "Seizure Memo" },
  { doc_type: "court_filing", label: "Court Filing" },
];

/*
 * Prototype recipients.
 */
const RECIPIENTS = [
  {
    username: "fo.rao",
    label: "Forensic Officer Rao",
    role: "forensic_officer",
  },
  {
    username: "pp.iyer",
    label: "Public Prosecutor Iyer",
    role: "prosecutor",
  },
  {
    username: "cc.das",
    label: "Court Clerk Das",
    role: "court_clerk",
  },
  {
    username: "admin",
    label: "Case Records Admin",
    role: "admin",
  },
];

export default function DocumentsTab({ caseId, onChanged, autoOpenDocId }) {
  const [docs, setDocs] = useState([]);
  const [selected, setSelected] = useState(null);
  const [error, setError] = useState(null);
  const [showForm, setShowForm] = useState(false);

  /*
   * STANDARDIZED TEMPLATES
   */
  const [templates, setTemplates] = useState([]);
  const [selectedTemplate, setSelectedTemplate] = useState("");
  const [activeCard, setActiveCard] = useState(null);
  const [scanMode, setScanMode] = useState(false);
  const [scanFileName, setScanFileName] = useState("");
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [matters, setMatters] = useState([]);
  const [users, setUsers] = useState([]);

  /*
   * OPENING A DOCUMENT — its actual readable content, fetched on demand
   * when a document is selected. Previously nothing ever called the
   * content endpoint, so a document could be selected and show its
   * status/history but never its substance — this is the fix for that.
   */
  const [content, setContent] = useState(null);
  const [contentLoading, setContentLoading] = useState(false);
  const [contentError, setContentError] = useState(null);
  const [viewVersionId, setViewVersionId] = useState(null);
  const [lockStatus, setLockStatus] = useState(null);
  const [myAccessRequests, setMyAccessRequests] = useState([]);
  const [ownerRequests, setOwnerRequests] = useState([]);
  const [requestMode, setRequestMode] = useState("view");
  const [decisionDrafts, setDecisionDrafts] = useState({}); // { [requestId]: { mode, days } }
  const [authorizedOfficers, setAuthorizedOfficers] = useState([]);
  const [now, setNow] = useState(() => new Date());

  // Tick every 30s so any "Expires in Xd Yh" countdown stays live.
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 30000);
    return () => clearInterval(id);
  }, []);

  function timeRemaining(expiresAtIso) {
    if (!expiresAtIso) return null;
    const diffMs = new Date(expiresAtIso).getTime() - now.getTime();
    if (diffMs <= 0) return null;
    const days = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    const hours = Math.floor((diffMs % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
    if (days > 0) return `${days}d ${hours}h left`;
    const mins = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));
    return `${hours}h ${mins}m left`;
  }

  const { user } = useAuth();

  /*
   * New document form.
   */
  const [form, setForm] = useState({
    doc_type: "fir",
    title: "",
    origin_type: "born_digital",
    initial_content: "",
    template_id: null,
    matter_id: null,
  });

  /*
   * ---------------------------------------------------------
   * OPEN A DOCUMENT'S CONTENT
   * ---------------------------------------------------------
   * Fires whenever a different document (or a different version of the
   * same document) is chosen to view. This is what actually makes a
   * transferred document "openable" for the receiving officer, not just
   * visible in a list.
   */
  function openDocument(doc, versionId) {
    setSelected(doc);
    setViewVersionId(versionId || null);
    setContent(null);
    setContentError(null);
    setLockStatus(null);
    setMyAccessRequests([]);
    setOwnerRequests([]);
    setContentLoading(true);

    api
      .getLockStatus(doc.id)
      .then((lock) => {
        setLockStatus(lock);
        if (lock.unlocked) {
          return api.getDocumentContent(doc.id, versionId).then(setContent);
        }
        return null;
      })
      .catch((e) => setContentError(e.message))
      .finally(() => setContentLoading(false));

    // If I own this document, load who's asking for it and who currently
    // holds a grant on it.
    api.listAccessRequestsForDocument(doc.id).then((rows) => {
      if (user && doc.created_by_id === user.id) {
        setOwnerRequests(rows.filter((r) => r.status === "pending"));
      } else {
        setMyAccessRequests(rows);
      }
    }).catch(() => {});

    setAuthorizedOfficers([]);
    if (user && doc.created_by_id === user.id) {
      api.listAuthorizedOfficers(doc.id).then(setAuthorizedOfficers).catch(() => {});
    }
  }

  function ownerName(doc) {
    if (!doc) return "";
    if (user && doc.created_by_id === user.id) return "You";
    return users.find((u) => u.id === doc.created_by_id)?.full_name || "Unknown";
  }

  async function requestAccess(doc, mode) {
    const chosenMode = mode || requestMode;
    const reason = prompt(`Why do you need ${chosenMode.toUpperCase()} access to ${doc.doc_ref}? (visible to whoever uploaded it)`);
    if (reason === null) return;
    setContentError(null);
    try {
      await api.requestDocumentAccess(doc.id, reason, chosenMode);
      openDocument(doc);
    } catch (err) {
      setContentError(err.message);
    }
  }

  function draftFor(reqId) {
    return decisionDrafts[reqId] || { mode: null, days: 7 };
  }

  function setDraft(reqId, patch) {
    setDecisionDrafts((d) => ({ ...d, [reqId]: { ...draftFor(reqId), ...patch } }));
  }

  async function decideAccess(req, decision) {
    setContentError(null);
    if (decision === "approved") {
      const draft = draftFor(req.id);
      const mode = draft.mode || req.requested_mode;
      const days = Number(draft.days) || 7;
      const ok = confirm(
        `Approve ${mode.toUpperCase()} access for ${days} day(s) to ${req.requested_by_name}?`
      );
      if (!ok) return;
      try {
        await api.decideDocumentAccess(req.id, "approved", "", mode, days);
        openDocument(selected);
      } catch (err) {
        setContentError(err.message);
      }
      return;
    }
    const reason = prompt("Reason (optional):") || "";
    try {
      await api.decideDocumentAccess(req.id, "rejected", reason);
      openDocument(selected);
    } catch (err) {
      setContentError(err.message);
    }
  }

  async function revokeAccess(officerRow) {
    if (!confirm(`Revoke ${officerRow.user_name}'s access now?`)) return;
    setContentError(null);
    try {
      await api.revokeDocumentAccess(officerRow.request_id);
      openDocument(selected);
    } catch (err) {
      setContentError(err.message);
    }
  }

  const isScannedContent = content && content.content.startsWith("data:");
  const scannedMime = isScannedContent ? content.content.slice(5, content.content.indexOf(";")) : null;

  /*
   * Arriving here from the Inbox (?openDoc=<id>) should open that exact
   * document immediately, not just land on the tab. Runs once per
   * caseId/autoOpenDocId pair.
   */
  const autoOpenedFor = useRef(null);
  useEffect(() => {
    if (!autoOpenDocId || autoOpenedFor.current === autoOpenDocId) return;
    const target = docs.find((d) => d.id === autoOpenDocId);
    if (target) {
      autoOpenedFor.current = autoOpenDocId;
      openDocument(target);
    }
  }, [autoOpenDocId, docs]);

  /*
   * ---------------------------------------------------------
   * LOAD DOCUMENTS
   * ---------------------------------------------------------
   */
  function load() {
    setError(null);

    api
      .listDocuments(caseId)
      .then((data) => {
        setDocs(data);

        if (selected) {
          const fresh = data.find(
            (x) => x.id === selected.id
          );

          setSelected(fresh || null);
        }
      })
      .catch((e) => {
        setError(e.message);
      });
  }

  /*
   * ---------------------------------------------------------
   * LOAD STANDARDIZED TEMPLATES
   * ---------------------------------------------------------
   */
  function loadTemplates() {
    api
      .listTemplates()
      .then((data) => {
        setTemplates(Array.isArray(data) ? data : []);
      })
      .catch((e) => {
        /*
         * Do not break the document page if templates
         * are unavailable.
         */
        console.error("Template loading failed:", e);
      });
  }

  useEffect(() => {
    load();
    loadTemplates();
    api.listCaseMatters(caseId).then(setMatters).catch(() => {});
    api.listUsers().then(setUsers).catch(() => {});
  }, [caseId]);

  /*
   * ---------------------------------------------------------
   * ONE-CLICK TEMPLATE CARD
   * ---------------------------------------------------------
   *
   * Clicking a card immediately opens the fill panel for that
   * document type — no dropdown browsing. The template (if one
   * exists for that doc_type) is linked via template_id but the
   * content area always starts blank: the officer types the
   * document directly, or switches to "Upload a scanned copy".
   */
  function pickCard(docType, label) {
    const template = templates.find((t) => t.doc_type === docType);
    setActiveCard({ doc_type: docType, label });
    setSelectedTemplate(template ? template.id : "");
    setScanMode(false);
    setScanFileName("");
    setForm({
      doc_type: docType,
      title: label,
      origin_type: "born_digital",
      initial_content: "",
      template_id: template ? template.id : null,
      matter_id: null,
    });
  }

  function backToCards() {
    setActiveCard(null);
    setScanMode(false);
    setScanFileName("");
  }

  /*
   * ---------------------------------------------------------
   * SCAN UPLOAD
   * ---------------------------------------------------------
   *
   * No binary file storage endpoint exists yet, so the scanned
   * file's bytes are captured as a base64 string and sent through
   * the same initial_content field a typed document uses — it is
   * still hashed (SHA-256) and version-controlled exactly like any
   * other document. This keeps the chain-of-custody/integrity
   * guarantees intact for scanned material without needing a
   * separate object-storage upload path.
   */
  function handleScanFile(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setScanFileName(file.name);
    const reader = new FileReader();
    reader.onload = () => {
      setForm((f) => ({ ...f, initial_content: String(reader.result), origin_type: "scanned" }));
    };
    reader.readAsDataURL(file);
  }

  function toggleScanMode(on) {
    setScanMode(on);
    setScanFileName("");
    setForm((f) => ({
      ...f,
      origin_type: on ? "scanned" : "born_digital",
      initial_content: "",
    }));
  }

  /*
   * ---------------------------------------------------------
   * CREATE DOCUMENT
   * ---------------------------------------------------------
   */
  async function createDoc(e) {
    e.preventDefault();
    setError(null);

    try {
      await api.createDocument({
        case_id: caseId,
        ...form,
      });

      /*
       * Reset form.
       */
      setForm({
        doc_type: "fir",
        title: "",
        origin_type: "born_digital",
        initial_content: "",
        template_id: null,
        matter_id: null,
      });

      setSelectedTemplate("");
      setActiveCard(null);
      setScanMode(false);
      setScanFileName("");
      setShowForm(false);

      load();
      onChanged?.();
    } catch (err) {
      setError(err.message);
    }
  }

  /*
   * ---------------------------------------------------------
   * DOCUMENT TRANSITION
   * ---------------------------------------------------------
   */
  async function doTransition(doc, action) {
    setError(null);

    let destination = null;

    if (action === "transfer") {
      if (!user) {
        setError(
          "You must be logged in to transfer a document."
        );
        return;
      }

      let availableRecipients = [];

      if (
        user.role === "investigating_officer"
      ) {
        availableRecipients =
          RECIPIENTS.filter(
            (r) => r.role === "forensic_officer"
          );
      } else if (
        user.role === "forensic_officer"
      ) {
        availableRecipients =
          RECIPIENTS.filter(
            (r) => r.role === "prosecutor"
          );
      } else if (
        user.role === "prosecutor"
      ) {
        availableRecipients =
          RECIPIENTS.filter(
            (r) => r.role === "court_clerk"
          );
      } else if (
        user.role === "admin"
      ) {
        availableRecipients = RECIPIENTS;
      }

      if (availableRecipients.length === 0) {
        setError(
          "No valid recipient is available for this role."
        );
        return;
      }

      const recipientText =
        availableRecipients
          .map(
            (r, index) =>
              `${index + 1}. ${r.label} (${r.username})`
          )
          .join("\n");

      const choice = prompt(
        `Transfer document to:\n\n${recipientText}\n\nEnter username exactly:`
      );

      if (choice === null) {
        return;
      }

      destination = choice.trim();

      const validRecipient =
        availableRecipients.some(
          (r) => r.username === destination
        );

      if (!validRecipient) {
        setError(
          "Invalid recipient. Please use one of the usernames shown."
        );
        return;
      }
    }

    try {
      await api.transitionDocument(doc.id, {
        action,
        destination,
      });

      load();
      onChanged?.();
    } catch (err) {
      setError(err.message);
    }
  }

  /*
   * ---------------------------------------------------------
   * CREATE NEW VERSION
   * ---------------------------------------------------------
   */
  async function addVersion(doc) {
    const content = prompt(
      "New version content:"
    );

    if (!content) {
      return;
    }

    const reason =
      prompt("Reason for revision:") ||
      "Revision";

    setError(null);

    try {
      await api.newVersion(doc.id, {
        content,
        reason,
      });

      load();
      onChanged?.();
    } catch (err) {
      setError(err.message);
    }
  }

  /*
   * ---------------------------------------------------------
   * VERIFY SHA-256
   * ---------------------------------------------------------
   */
  async function verify(doc, version) {
    setError(null);

    try {
      const result =
        await api.verifyVersion(
          doc.id,
          version.id
        );

      alert(
        result.verified
          ? `✓ INTEGRITY VERIFIED

Version: ${result.version_no}

Recorded SHA-256:
${result.recorded_hash}

Recalculated SHA-256:
${result.recalculated_hash}`
          : `✕ INTEGRITY FAILURE

Version: ${result.version_no}

Recorded SHA-256:
${result.recorded_hash}

Recalculated SHA-256:
${result.recalculated_hash}

Stored content does not match the recorded hash.
This event has been logged.`
      );

      load();
    } catch (err) {
      setError(err.message);
    }
  }

  /*
   * ---------------------------------------------------------
   * MOCK CCTNS / E-COURTS
   * ---------------------------------------------------------
   */
  async function adapterAction(doc, which) {
    setError(null);

    try {
      if (which === "cctns") {
        await api.adapterCctnsReceive(
          caseId,
          doc.id
        );
      } else {
        await api.adapterEcourtsSend(
          caseId,
          doc.id
        );
      }

      load();
      onChanged?.();
    } catch (err) {
      setError(err.message);
    }
  }

  async function assignMatter(doc, matterId) {
    setError(null);
    try {
      await api.assignDocumentMatter(doc.id, matterId || null);
      load();
      onChanged?.();
    } catch (err) {
      setError(err.message);
    }
  }

  /*
   * ---------------------------------------------------------
   * REQUEST DISCLOSURE TO DEFENCE
   * ---------------------------------------------------------
   *
   * The only path by which any document reaches the defence side.
   * Only Prosecutor / Court Clerk can raise this; only Admin can
   * approve it (see the Admin tab). Raising the request never
   * grants access by itself.
   */
  async function requestDisclosure(doc) {
    const reason = prompt(
      "Reason for disclosure request (e.g. Sec 230 BNSS — accused's advocate entitled to this document):"
    );
    if (reason === null) return;

    setError(null);

    try {
      await api.requestDisclosure(caseId, doc.id, reason);
      alert("Disclosure request sent to Admin for approval.");
    } catch (err) {
      setError(err.message);
    }
  }

  /*
   * ---------------------------------------------------------
   * POLICY ENGINE - UI VIEW
   * ---------------------------------------------------------
   */
  function getActionsForUser(doc) {
    if (!user) {
      return [];
    }

    const rolePolicy =
      ROLE_ACTIONS[user.role];

    if (!rolePolicy) {
      return [];
    }

    return rolePolicy[doc.status] || [];
  }

  return (
    <div
      style={{
        display: "flex",
        gap: 18,
      }}
    >

      {/* =====================================================
          LEFT SIDE
          ===================================================== */}

      <div
        style={{
          flex: "0 0 340px",
        }}
      >

        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <h3 style={{ margin: 0 }}>
            Documents
          </h3>

          <button
            className="btn"
            onClick={() => {
              setShowForm((s) => !s);
              setActiveCard(null);
              setScanMode(false);
            }}
          >
            {showForm ? "Cancel" : "+ New"}
          </button>
        </div>

        {/* =================================================
            ONE-CLICK TEMPLATE CARDS + TYPE-OR-SCAN PANEL
            ================================================= */}

        {showForm && !activeCard && (
          <div className="card" style={{ marginTop: 10 }}>
            <div className="hint" style={{ marginBottom: 8 }}>
              Choose a standardized template — opens straight to a fill-in space, one click.
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
              {CARDS.map((c) => (
                <button
                  key={c.doc_type}
                  className="btn secondary"
                  onClick={() => pickCard(c.doc_type, c.label)}
                >
                  {c.label}
                </button>
              ))}
            </div>
          </div>
        )}

        {showForm && activeCard && (
          <div className="card" style={{ marginTop: 10 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <strong>{activeCard.label}</strong>
              <button type="button" className="btn secondary" onClick={backToCards}>← Back</button>
            </div>

            <div className="hint" style={{ marginTop: 6, marginBottom: 10 }}>
              Case ID: <strong>{caseId}</strong>
            </div>

            <form onSubmit={createDoc}>
              <label>Title</label>
              <input
                value={form.title}
                onChange={(e) => setForm({ ...form, title: e.target.value })}
                required
              />

              <label>Matter (event / incident this belongs to)</label>
              <select
                value={form.matter_id || ""}
                onChange={(e) => setForm({ ...form, matter_id: e.target.value || null })}
              >
                <option value="">— none —</option>
                {matters.map((m) => (
                  <option key={m.id} value={m.id}>{m.title}</option>
                ))}
              </select>
              {matters.length === 0 && (
                <div className="hint" style={{ marginTop: -4, marginBottom: 8 }}>
                  No matters yet — create one in the Matters tab to group related documents and evidence together.
                </div>
              )}

              <div style={{ display: "flex", gap: 8, marginBottom: 10 }}>
                <button
                  type="button"
                  className={scanMode ? "btn secondary" : "btn"}
                  onClick={() => toggleScanMode(false)}
                >
                  Type it
                </button>
                <button
                  type="button"
                  className={scanMode ? "btn" : "btn secondary"}
                  onClick={() => toggleScanMode(true)}
                >
                  Upload a scanned copy
                </button>
              </div>

              {!scanMode && (
                <>
                  <label>Type your {activeCard.label} here</label>
                  <textarea
                    rows={8}
                    value={form.initial_content}
                    onChange={(e) => setForm({ ...form, initial_content: e.target.value })}
                    placeholder={`Enter the full ${activeCard.label} details...`}
                    required
                  />
                </>
              )}

              {scanMode && (
                <>
                  <label>Scanned file</label>
                  <input type="file" onChange={handleScanFile} required={!form.initial_content} />
                  {scanFileName && (
                    <div className="hint" style={{ marginBottom: 8 }}>
                      Selected: {scanFileName} — will be hashed (SHA-256) and stored as version 1.
                    </div>
                  )}
                </>
              )}

              <button
                type="button"
                className="link"
                style={{ fontSize: 12, marginBottom: 8, display: "inline-block" }}
                onClick={() => setShowAdvanced((s) => !s)}
              >
                {showAdvanced ? "Hide advanced options" : "Advanced options (document type / origin)"}
              </button>

              {showAdvanced && (
                <>
                  <label>Document Type</label>
                  <select
                    value={form.doc_type}
                    onChange={(e) => setForm({ ...form, doc_type: e.target.value })}
                  >
                    {DOC_TYPES.map((t) => (
                      <option key={t} value={t}>{t.replaceAll("_", " ")}</option>
                    ))}
                  </select>

                  <label>Origin</label>
                  <select
                    value={form.origin_type}
                    onChange={(e) => setForm({ ...form, origin_type: e.target.value })}
                  >
                    <option value="born_digital">Born digital</option>
                    <option value="scanned">Scanned</option>
                    <option value="received_external">Received from external system</option>
                  </select>
                </>
              )}

              <button className="btn" style={{ width: "100%", marginTop: 6 }}>
                Save {activeCard.label}
              </button>
            </form>
          </div>
        )}

        {/* =================================================
            DOCUMENT LIST
            ================================================= */}

        <div
          className="card"
          style={{
            marginTop: 10,
            padding: 0,
          }}
        >

          {docs.map((d) => (
            <div
              key={d.id}
              onClick={() =>
                openDocument(d)
              }
              style={{
                padding: "10px 14px",
                borderBottom:
                  "1px solid #EEE",
                cursor: "pointer",
                background:
                  selected?.id === d.id
                    ? "var(--accent-tint)"
                    : "white",
              }}
            >

              <div
                style={{
                  fontSize: 12.5,
                  color: "var(--gray)",
                }}
              >
                {d.doc_ref}
              </div>

              <div
                style={{
                  fontWeight: 600,
                }}
              >
                {d.title}
              </div>

              <span
                className={`badge ${d.status}`}
              >
                {d.status.replaceAll(
                  "_",
                  " "
                )}
              </span>

            </div>
          ))}

          {docs.length === 0 && (
            <div
              className="hint"
              style={{ padding: 14 }}
            >
              No documents in this case yet.
            </div>
          )}

        </div>

      </div>

      {/* =====================================================
          RIGHT SIDE
          ===================================================== */}

      <div style={{ flex: 1 }}>

        {error && (
          <div className="error-banner">
            {error}
          </div>
        )}

        {!selected && (
          <div className="hint">
            Select a document to view
            its full identity and history.
          </div>
        )}

        {selected && (
          <div className="card">

            <div className="hint">
              {selected.doc_ref}
            </div>

            <h3>
              {selected.title}
            </h3>

            <div>

              <span
                className={`badge ${selected.status}`}
              >
                {selected.status.replaceAll(
                  "_",
                  " "
                )}
              </span>{" "}

              <span className="badge">
                {selected.doc_type.replaceAll(
                  "_",
                  " "
                )}
              </span>{" "}

              <span className="badge">
                {selected.origin_type.replaceAll(
                  "_",
                  " "
                )}
              </span>{" "}

              <span className="badge" style={{ background: "#EFE7F9", color: "#5B3A8C" }}>
                Uploaded by: {ownerName(selected)}
              </span>

            </div>

            {/* =================================================
                DOCUMENT CONTENT — the actual "open it" view
                ================================================= */}

            <div
              style={{
                marginTop: 14,
                border: "1px solid #EEE",
                borderRadius: 6,
                padding: 12,
                background: "#FAFAFA",
              }}
            >
              <strong style={{ fontSize: 13 }}>Document Content</strong>

              {contentLoading && (
                <div className="hint" style={{ marginTop: 8 }}>Opening document...</div>
              )}

              {contentError && (
                <div className="error-banner" style={{ marginTop: 8 }}>
                  Could not open this document: {contentError}
                </div>
              )}

              {!contentLoading && lockStatus && !lockStatus.unlocked && (
                <div style={{ marginTop: 10 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
                    <span style={{ fontSize: 20 }}>🔒</span>
                    <strong>Locked</strong>
                  </div>
                  <div className="hint" style={{ marginBottom: 10 }}>
                    This document is locked. Request access and it will be reviewed and approved
                    or rejected, with a set amount of time it stays available — this is never decided by Admin.
                  </div>

                  {!lockStatus.my_request_status && (
                    <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                      <select value={requestMode} onChange={(e) => setRequestMode(e.target.value)}>
                        <option value="view">View</option>
                        <option value="edit">Edit</option>
                        <option value="append">Append</option>
                      </select>
                      <button className="btn secondary" onClick={() => requestAccess(selected, requestMode)}>
                        Request Access
                      </button>
                    </div>
                  )}
                  {lockStatus.my_request_status === "pending" && (
                    <span className="badge">Request pending — awaiting approval</span>
                  )}
                  {lockStatus.my_request_status === "approved" && lockStatus.my_expires_at && (
                    <div
                      style={{
                        border: "1px solid #DDD", borderRadius: 6, padding: "8px 12px",
                        display: "inline-block", background: "#F2F8F0",
                      }}
                    >
                      Mode: <strong>{(lockStatus.my_granted_mode || "").toUpperCase()}</strong>
                      {" · "}
                      {timeRemaining(lockStatus.my_expires_at)
                        ? <>Expires in {timeRemaining(lockStatus.my_expires_at)}</>
                        : <strong>Access expired — request again</strong>}
                    </div>
                  )}
                  {lockStatus.my_request_status === "approved" && !lockStatus.my_expires_at && (
                    <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                      <span className="badge" style={{ background: "#FBE8E6", color: "#A3453D" }}>
                        Access expired — request again
                      </span>
                      <select value={requestMode} onChange={(e) => setRequestMode(e.target.value)}>
                        <option value="view">View</option>
                        <option value="edit">Edit</option>
                        <option value="append">Append</option>
                      </select>
                      <button className="btn secondary" onClick={() => requestAccess(selected, requestMode)}>
                        Request Again
                      </button>
                    </div>
                  )}
                  {lockStatus.my_request_status === "rejected" && (
                    <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                      <span className="badge" style={{ background: "#FBE8E6", color: "#A3453D" }}>
                        Request rejected
                      </span>
                      <select value={requestMode} onChange={(e) => setRequestMode(e.target.value)}>
                        <option value="view">View</option>
                        <option value="edit">Edit</option>
                        <option value="append">Append</option>
                      </select>
                      <button className="btn secondary" onClick={() => requestAccess(selected, requestMode)}>
                        Request Again
                      </button>
                    </div>
                  )}
                </div>
              )}

              {ownerRequests.length > 0 && (
                <div style={{ marginTop: 12, borderTop: "1px solid #EEE", paddingTop: 10 }}>
                  <strong style={{ fontSize: 13 }}>Requests waiting on your approval (you uploaded this document)</strong>
                  {ownerRequests.map((r) => {
                    const draft = draftFor(r.id);
                    const mode = draft.mode || r.requested_mode;
                    return (
                      <div key={r.id} style={{ marginTop: 8, paddingBottom: 8, borderBottom: "1px solid #F3F3F3" }}>
                        <div>
                          <strong>{r.requested_by_name}</strong>{" "}
                          <span className="badge">requested {r.requested_mode}</span>
                        </div>
                        {r.reason && <div className="hint">{r.reason}</div>}
                        <div style={{ marginTop: 6, display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                          <label className="hint" style={{ fontSize: 11 }}>
                            Grant mode:{" "}
                            <select value={mode} onChange={(e) => setDraft(r.id, { mode: e.target.value })}>
                              <option value="view">View</option>
                              <option value="edit">Edit</option>
                              <option value="append">Append</option>
                            </select>
                          </label>
                          <label className="hint" style={{ fontSize: 11 }}>
                            Days:{" "}
                            <input
                              type="number" min={1} style={{ width: 60 }}
                              value={draft.days ?? 7}
                              onChange={(e) => setDraft(r.id, { days: e.target.value })}
                            />
                          </label>
                          <button className="btn secondary" onClick={() => setDraft(r.id, { days: 1 })}>1 day</button>
                          <button className="btn secondary" onClick={() => setDraft(r.id, { days: 7 })}>7 days</button>
                          <button className="btn secondary" onClick={() => decideAccess(r, "approved")}>Approve</button>
                          <button className="btn danger" onClick={() => decideAccess(r, "rejected")}>Reject</button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
              {authorizedOfficers.length > 0 && (
                <div style={{ marginTop: 12, borderTop: "1px solid #EEE", paddingTop: 10 }}>
                  <strong style={{ fontSize: 13 }}>Authorized officers (you uploaded this document)</strong>
                  <table style={{ marginTop: 6 }}>
                    <thead>
                      <tr><th>Name</th><th>Role</th><th>Mode</th><th>Granted</th><th>Expires</th><th>Status</th><th></th></tr>
                    </thead>
                    <tbody>
                      {authorizedOfficers.map((o) => (
                        <tr key={o.request_id} style={{ opacity: o.status === "active" ? 1 : 0.55 }}>
                          <td>{o.user_name}</td>
                          <td>{o.role}</td>
                          <td>{(o.mode || "").toUpperCase()}</td>
                          <td>{o.granted_at ? new Date(o.granted_at).toLocaleDateString() : "—"}</td>
                          <td>{o.expires_at ? new Date(o.expires_at).toLocaleDateString() : "—"}</td>
                          <td><span className="badge">{o.status}</span></td>
                          <td>
                            {o.status === "active" && (
                              <button className="btn danger" onClick={() => revokeAccess(o)}>Revoke</button>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {!contentLoading && !contentError && content && (
                <div style={{ marginTop: 8 }}>
                  <div className="hint" style={{ marginBottom: 6 }}>
                    Version {content.version_no} · SHA-256 {content.sha256_hash.slice(0, 16)}...
                  </div>

                  {isScannedContent && scannedMime && scannedMime.startsWith("image/") && (
                    <img
                      src={content.content}
                      alt={selected.title}
                      style={{ maxWidth: "100%", borderRadius: 4, border: "1px solid #DDD" }}
                    />
                  )}

                  {isScannedContent && scannedMime === "application/pdf" && (
                    <iframe
                      src={content.content}
                      title={selected.title}
                      style={{ width: "100%", height: 420, border: "1px solid #DDD", borderRadius: 4 }}
                    />
                  )}

                  {isScannedContent && !(scannedMime && (scannedMime.startsWith("image/") || scannedMime === "application/pdf")) && (
                    <a
                      className="btn secondary"
                      href={content.content}
                      download={`${selected.doc_ref}`}
                    >
                      Download scanned file ({scannedMime || "file"})
                    </a>
                  )}

                  {!isScannedContent && (
                    <pre
                      style={{
                        whiteSpace: "pre-wrap",
                        wordBreak: "break-word",
                        maxHeight: 320,
                        overflowY: "auto",
                        background: "white",
                        border: "1px solid #EEE",
                        borderRadius: 4,
                        padding: 10,
                        margin: 0,
                        fontFamily: "inherit",
                        fontSize: 13,
                      }}
                    >
                      {content.content}
                    </pre>
                  )}
                </div>
              )}
            </div>

            {/* CASE ID */}

            <div
              className="hint"
              style={{
                marginTop: 10,
              }}
            >
              Case ID:{" "}
              <strong>{caseId}</strong>
            </div>

            {/* CURRENT USER */}

            {user && (
              <div
                className="hint"
                style={{
                  marginTop: 6,
                }}
              >
                Logged in as:{" "}
                <strong>
                  {user.full_name}
                </strong>
                {" · "}
                {user.role.replaceAll(
                  "_",
                  " "
                )}
              </div>
            )}

            {/* =================================================
                ACTIONS
                ================================================= */}

            <div
              style={{
                marginTop: 14,
              }}
            >

              <strong>
                Actions
              </strong>

              <div
                style={{
                  marginTop: 6,
                  display: "flex",
                  flexWrap: "wrap",
                  gap: 8,
                }}
              >

                {getActionsForUser(
                  selected
                ).map(
                  ([action, label]) => (
                    <button
                      key={action}
                      className="btn secondary"
                      onClick={() =>
                        doTransition(
                          selected,
                          action
                        )
                      }
                    >
                      {label}
                    </button>
                  )
                )}

                <button
                  className="btn secondary"
                  onClick={() =>
                    addVersion(selected)
                  }
                >
                  + New Version
                </button>

                {user && ["prosecutor", "court_clerk"].includes(user.role) && (
                  <button
                    className="btn secondary"
                    onClick={() => requestDisclosure(selected)}
                  >
                    Request Disclosure to Defence
                  </button>
                )}

              </div>

              <div style={{ marginTop: 14 }}>
                <label style={{ fontSize: 12 }}>Matter</label>
                <select
                  value={selected.matter_id || ""}
                  onChange={(e) => assignMatter(selected, e.target.value)}
                >
                  <option value="">— none —</option>
                  {matters.map((m) => (
                    <option key={m.id} value={m.id}>{m.title}</option>
                  ))}
                </select>
              </div>

              <div
                className="hint"
                style={{
                  marginTop: 6,
                }}
              >
                Actions are determined by
                your role and document state.
                The backend policy engine
                independently checks every action.
              </div>

            </div>

            {/* =================================================
                DOCUMENT HOLDER
                ================================================= */}

            {selected.current_holder_id && (
              <div
                className="hint"
                style={{
                  marginTop: 10,
                }}
              >
                Current document holder:
                <strong>
                  {" "}
                  assigned user
                </strong>
              </div>
            )}

            {/* =================================================
                MOCK ADAPTERS
                ================================================= */}

            <div
              style={{
                marginTop: 16,
              }}
            >

              <strong>
                Mock adapters
              </strong>

              <div
                className="hint"
                style={{
                  marginTop: 4,
                }}
              >
                Prototype only — no live
                government API.
              </div>

              <div
                style={{
                  marginTop: 6,
                  display: "flex",
                  gap: 8,
                }}
              >

                <button
                  className="btn secondary"
                  onClick={() =>
                    adapterAction(
                      selected,
                      "cctns"
                    )
                  }
                >
                  Receive from Mock CCTNS
                </button>

                <button
                  className="btn secondary"
                  onClick={() =>
                    adapterAction(
                      selected,
                      "ecourts"
                    )
                  }
                >
                  Send to Mock e-Courts
                </button>

              </div>

            </div>

            {/* =================================================
                VERSION HISTORY
                ================================================= */}

            <div
              style={{
                marginTop: 18,
              }}
            >

              <strong>
                Version History
              </strong>

              <table
                style={{
                  marginTop: 8,
                }}
              >

                <thead>
                  <tr>
                    <th>V</th>
                    <th>Hash</th>
                    <th>Prev Hash</th>
                    <th>By</th>
                    <th>Reason</th>
                    <th></th>
                  </tr>
                </thead>

                <tbody>

                  {selected.versions.map(
                    (v) => (
                      <tr
                        key={v.id}
                        style={{
                          opacity:
                            v.superseded
                              ? 0.55
                              : 1,
                        }}
                      >

                        <td>
                          {v.version_no}
                          {v.superseded &&
                            " (superseded)"}
                        </td>

                        <td
                          style={{
                            fontFamily:
                              "monospace",
                            fontSize: 11,
                          }}
                        >
                          {v.sha256_hash.slice(
                            0,
                            14
                          )}
                          ...
                        </td>

                        <td
                          style={{
                            fontFamily:
                              "monospace",
                            fontSize: 11,
                          }}
                        >
                          {v.prev_version_hash
                            ? v.prev_version_hash.slice(
                                0,
                                14
                              ) + "..."
                            : "—"}
                        </td>

                        <td>
                          {v.created_by_name}
                        </td>

                        <td>
                          {v.reason || "—"}
                        </td>

                        <td>

                          <button
                            className="btn secondary"
                            style={{ marginRight: 6 }}
                            onClick={() =>
                              openDocument(selected, v.id)
                            }
                          >
                            Open
                          </button>

                          <button
                            className="btn secondary"
                            onClick={() =>
                              verify(
                                selected,
                                v
                              )
                            }
                          >
                            Verify
                          </button>

                        </td>

                      </tr>
                    )
                  )}

                </tbody>

              </table>

            </div>

          </div>
        )}

      </div>

    </div>
  );
}