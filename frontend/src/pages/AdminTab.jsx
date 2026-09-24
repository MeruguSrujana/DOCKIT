import { useEffect, useState } from "react";
import { api } from "../api";

const STATUS_COLORS = {
  not_started: { bg: "#EEE", fg: "#6B6B6B" },
  draft: { bg: "#EEE", fg: "#6B6B6B" },
  registered: { bg: "#E4EDEE", fg: "#36454F" },
  under_review: { bg: "#FCEFD8", fg: "#8A5A00" },
  approved: { bg: "#DCEEE0", fg: "#1E5631" },
  transferred: { bg: "#E0E8F5", fg: "#2D4A8A" },
  received: { bg: "#E0E8F5", fg: "#2D4A8A" },
  archived: { bg: "#DCEEE0", fg: "#1E5631" },
};

function FlowChart({ caseId }) {
  const [flow, setFlow] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.getCaseFlow(caseId).then(setFlow).catch((e) => setError(e.message));
  }, [caseId]);

  if (error) return <div className="error-banner">{error}</div>;
  if (!flow) return <div className="hint">Loading flow...</div>;

  return (
    <div className="card">
      <h3 style={{ marginTop: 0 }}>Case Flow (status only — no content shown)</h3>
      <div className="hint" style={{ marginBottom: 14 }}>
        This is the only case view Admin needs day-to-day: which stage each document type has reached.
      </div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 10, alignItems: "center" }}>
        {flow.stages.map((s, i) => {
          const c = STATUS_COLORS[s.status] || STATUS_COLORS.not_started;
          return (
            <div key={s.doc_type} style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <div
                style={{
                  background: c.bg, color: c.fg, borderRadius: 8, padding: "10px 14px",
                  minWidth: 130, textAlign: "center", border: "1px solid rgba(0,0,0,0.06)",
                }}
              >
                <div style={{ fontWeight: 700, fontSize: 12.5 }}>{s.stage}</div>
                <div style={{ fontSize: 11, marginTop: 3 }}>{s.status.replaceAll("_", " ")}</div>
              </div>
              {i < flow.stages.length - 1 && <span style={{ color: "#BBB", fontSize: 18 }}>→</span>}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function AccessControl({ caseId, caseObj, onCaseChanged }) {
  const [collaborators, setCollaborators] = useState([]);
  const [users, setUsers] = useState([]);
  const [error, setError] = useState(null);
  const [userId, setUserId] = useState("");
  const [roleLabel, setRoleLabel] = useState("");

  function load() {
    api.listCollaborators(caseId).then(setCollaborators).catch((e) => setError(e.message));
    api.listUsers().then(setUsers).catch(() => {});
  }
  useEffect(load, [caseId]);

  async function addPerson(e) {
    e.preventDefault();
    if (!userId || !roleLabel.trim()) return;
    setError(null);
    try {
      await api.addCollaborator(caseId, userId, roleLabel);
      setUserId("");
      setRoleLabel("");
      load();
    } catch (err) { setError(err.message); }
  }

  async function removePerson(c) {
    setError(null);
    try {
      await api.removeCollaborator(caseId, c.id);
      load();
    } catch (err) { setError(err.message); }
  }

  async function toggleRestricted() {
    setError(null);
    try {
      await api.setCaseRestricted(caseId, !caseObj.is_restricted);
      onCaseChanged();
    } catch (err) { setError(err.message); }
  }

  return (
    <div className="card">
      <h3 style={{ marginTop: 0 }}>Case Access</h3>
      {error && <div className="error-banner">{error}</div>}

      <div style={{ marginBottom: 14 }}>
        <span className="hint">
          {caseObj.is_restricted
            ? "This case is RESTRICTED — only the people below (plus Admin) can open it."
            : "This case is open to all authorized roles by default."}
        </span>{" "}
        <button className="btn secondary" style={{ marginLeft: 8 }} onClick={toggleRestricted}>
          {caseObj.is_restricted ? "Remove Restriction" : "Mark as Restricted"}
        </button>
      </div>

      <strong>Add or Remove Person</strong>
      <div className="hint" style={{ marginBottom: 8 }}>
        Bring in anyone outside the 4 core roles — e.g. a Cyber Expert, translator, or officer from another department — for this case only.
      </div>
      <form onSubmit={addPerson} style={{ display: "flex", gap: 8, alignItems: "flex-end", flexWrap: "wrap" }}>
        <div style={{ flex: "1 1 220px" }}>
          <label>Person</label>
          <select value={userId} onChange={(e) => setUserId(e.target.value)}>
            <option value="">— select —</option>
            {users.map((u) => <option key={u.id} value={u.id}>{u.full_name} ({u.role.replaceAll("_", " ")})</option>)}
          </select>
        </div>
        <div style={{ flex: "1 1 180px" }}>
          <label>Role on this case</label>
          <input value={roleLabel} onChange={(e) => setRoleLabel(e.target.value)} placeholder="e.g. Cyber Expert" />
        </div>
        <button className="btn" style={{ marginBottom: 10 }}>Add</button>
      </form>

      <table style={{ marginTop: 10 }}>
        <thead><tr><th>Person</th><th>Role on Case</th><th>Added By</th><th></th></tr></thead>
        <tbody>
          {collaborators.map((c) => (
            <tr key={c.id}>
              <td>{c.user_name}</td>
              <td><span className="badge">{c.role_label}</span></td>
              <td className="hint">{c.added_by_name}</td>
              <td><button className="btn danger" onClick={() => removePerson(c)}>Remove</button></td>
            </tr>
          ))}
          {collaborators.length === 0 && <tr><td colSpan={4} className="hint" style={{ padding: 10 }}>No extra people added to this case.</td></tr>}
        </tbody>
      </table>
    </div>
  );
}

function PendingApprovals({ caseId }) {
  const [reviews, setReviews] = useState([]);
  const [error, setError] = useState(null);

  function load() {
    api.listAdminReviews("pending").then((all) => setReviews(all.filter((r) => r.case_id === caseId)))
      .catch((e) => setError(e.message));
  }
  useEffect(load, [caseId]);

  async function decide(r, status) {
    const reason = status === "rejected" ? prompt("Reason for rejection (optional):") || "" : "";
    setError(null);
    try {
      await api.decideAdminReview(r.id, status, reason);
      load();
    } catch (err) { setError(err.message); }
  }

  return (
    <div className="card">
      <h3 style={{ marginTop: 0 }}>Pending Approvals</h3>
      <div className="hint" style={{ marginBottom: 10 }}>
        Metadata only — document content is never shown here. Approval is a procedural checkpoint, not a content review.
      </div>
      {error && <div className="error-banner">{error}</div>}
      <table>
        <thead><tr><th>Document Type</th><th>Submitted By</th><th>Submitted</th><th>Actions</th></tr></thead>
        <tbody>
          {reviews.map((r) => (
            <tr key={r.id}>
              <td><span className="badge">{r.doc_type.replaceAll("_", " ")}</span></td>
              <td>{r.submitted_by_name}</td>
              <td className="hint">{new Date(r.created_at).toLocaleString()}</td>
              <td>
                <button className="btn secondary" style={{ marginRight: 6 }} onClick={() => decide(r, "approved")}>Approve</button>
                <button className="btn danger" onClick={() => decide(r, "rejected")}>Reject</button>
              </td>
            </tr>
          ))}
          {reviews.length === 0 && <tr><td colSpan={4} className="hint" style={{ padding: 10 }}>Nothing pending.</td></tr>}
        </tbody>
      </table>
    </div>
  );
}

function Disclosures({ caseId }) {
  const [items, setItems] = useState([]);
  const [error, setError] = useState(null);

  function load() {
    api.listCaseDisclosures(caseId).then(setItems).catch((e) => setError(e.message));
  }
  useEffect(load, [caseId]);

  async function decide(d, status) {
    const reason = prompt(status === "approved" ? "Note (optional):" : "Reason for rejection:") || "";
    setError(null);
    try {
      await api.decideDisclosure(d.id, status, reason);
      load();
    } catch (err) { setError(err.message); }
  }

  return (
    <div className="card">
      <h3 style={{ marginTop: 0 }}>Disclosure Requests (to Defence)</h3>
      <div className="hint" style={{ marginBottom: 10 }}>
        The defence side has zero access by default. Only a Prosecutor or Court Clerk can request a specific
        document be released, and only Admin can approve it (Sec 230/231 BNSS).
      </div>
      {error && <div className="error-banner">{error}</div>}
      <table>
        <thead><tr><th>Document</th><th>Requested By</th><th>Reason</th><th>Status</th><th>Actions</th></tr></thead>
        <tbody>
          {items.map((d) => (
            <tr key={d.id}>
              <td><strong>{d.doc_ref}</strong><div className="hint">{d.doc_type.replaceAll("_", " ")}</div></td>
              <td>{d.requested_by_name}</td>
              <td>{d.reason || "—"}</td>
              <td><span className="badge">{d.status}</span></td>
              <td>
                {d.status === "pending" ? (
                  <>
                    <button className="btn secondary" style={{ marginRight: 6 }} onClick={() => decide(d, "approved")}>Approve</button>
                    <button className="btn danger" onClick={() => decide(d, "rejected")}>Reject</button>
                  </>
                ) : "—"}
              </td>
            </tr>
          ))}
          {items.length === 0 && <tr><td colSpan={5} className="hint" style={{ padding: 10 }}>No disclosure requests yet.</td></tr>}
        </tbody>
      </table>
    </div>
  );
}

export default function AdminTab({ caseId, caseObj, onCaseChanged }) {
  return (
    <div>
      <FlowChart caseId={caseId} />
      <AccessControl caseId={caseId} caseObj={caseObj} onCaseChanged={onCaseChanged} />
      <PendingApprovals caseId={caseId} />
      <Disclosures caseId={caseId} />
    </div>
  );
}
