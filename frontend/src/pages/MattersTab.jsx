import { useEffect, useState } from "react";
import { api } from "../api";

const STATUS_STYLES = {
  under_investigation: { bg: "#DCEAFB", fg: "#1E5FA8", label: "Under Investigation" },
  evidence_collection: { bg: "#FCEFD8", fg: "#8A5A00", label: "Evidence Collection" },
  pending_review: { bg: "#EFE7F9", fg: "#5B3A8C", label: "Pending Review" },
  closed: { bg: "#E4E4E4", fg: "#555", label: "Closed" },
};

const CIRCLE_COLORS = ["#2E5FA3", "#1E7A34", "#5B3A8C", "#B23A48", "#A87B00"];

function MatterCard({ matter, index, expanded, onToggle, onStatusChanged }) {
  const [docs, setDocs] = useState(null);
  const [evidence, setEvidence] = useState(null);
  const [witnesses, setWitnesses] = useState(null);

  async function changeStatus(e) {
    e.stopPropagation();
    const newStatus = e.target.value;
    try {
      await api.setMatterStatus(matter.id, newStatus);
      onStatusChanged();
    } catch (err) {
      alert(err.message);
    }
  }

  useEffect(() => {
    if (expanded && docs === null) {
      api.getMatterDocuments(matter.id).then(setDocs).catch(() => setDocs([]));
      api.getMatterEvidence(matter.id).then(setEvidence).catch(() => setEvidence([]));
      api.getMatterWitnesses(matter.id).then(setWitnesses).catch(() => setWitnesses([]));
    }
  }, [expanded]);

  const statusStyle = STATUS_STYLES[matter.status] || STATUS_STYLES.under_investigation;
  const circleColor = CIRCLE_COLORS[index % CIRCLE_COLORS.length];

  return (
    <div
      className="card"
      style={{ marginBottom: 12, cursor: "pointer" }}
      onClick={onToggle}
    >
      <div style={{ display: "flex", alignItems: "flex-start", gap: 14 }}>
        <div
          style={{
            width: 34, height: 34, borderRadius: "50%", background: circleColor, color: "white",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontWeight: 700, fontSize: 14, flexShrink: 0,
          }}
        >
          {index + 1}
        </div>

        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 10 }}>
            <div>
              <strong style={{ fontSize: 15 }}>{matter.title}</strong>
              {matter.key_question && (
                <div style={{ color: "#666", marginTop: 3, fontSize: 13.5 }}>{matter.key_question}</div>
              )}
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 10, flexShrink: 0 }}>
              <select
                value={matter.status}
                onChange={changeStatus}
                onClick={(e) => e.stopPropagation()}
                style={{
                  margin: 0, fontSize: 12, padding: "4px 8px", borderRadius: 12, border: "none",
                  background: statusStyle.bg, color: statusStyle.fg, fontWeight: 600,
                }}
              >
                <option value="under_investigation">Under Investigation</option>
                <option value="evidence_collection">Evidence Collection</option>
                <option value="pending_review">Pending Review</option>
                <option value="closed">Closed</option>
              </select>
              <span style={{ color: "#BBB", fontSize: 16 }}>{expanded ? "▾" : "›"}</span>
            </div>
          </div>

          <div style={{ display: "flex", flexWrap: "wrap", gap: 18, marginTop: 12, fontSize: 13, color: "#555" }}>
            <span>📄 {matter.document_count} Document{matter.document_count === 1 ? "" : "s"}</span>
            <span>👥 {matter.witness_count} Witness{matter.witness_count === 1 ? "" : "es"}</span>
            <span>🧪 {matter.evidence_count} Evidence</span>
            {matter.location && <span>📍 {matter.location}</span>}
          </div>
        </div>
      </div>

      {expanded && (
        <div style={{ marginTop: 16, borderTop: "1px solid #EEE", paddingTop: 14 }} onClick={(e) => e.stopPropagation()}>
          {matter.description && (
            <div className="hint" style={{ marginBottom: 12 }}>{matter.description}</div>
          )}

          <strong style={{ fontSize: 13 }}>Documents</strong>
          {docs === null && <div className="hint">Loading...</div>}
          {docs && docs.length === 0 && <div className="hint">None linked yet.</div>}
          {docs && docs.map((d) => (
            <div key={d.id} className="hint" style={{ marginTop: 4 }}>
              {d.doc_ref} — {d.title} <span className="badge">{d.status}</span>
            </div>
          ))}

          <strong style={{ fontSize: 13, display: "block", marginTop: 14 }}>Evidence</strong>
          {evidence === null && <div className="hint">Loading...</div>}
          {evidence && evidence.length === 0 && <div className="hint">None linked yet.</div>}
          {evidence && evidence.map((e) => (
            <div key={e.id} className="hint" style={{ marginTop: 4 }}>
              {e.evidence_code} — {e.description} <span className="badge">{e.status}</span>
            </div>
          ))}

          <strong style={{ fontSize: 13, display: "block", marginTop: 14 }}>Witnesses</strong>
          {witnesses === null && <div className="hint">Loading...</div>}
          {witnesses && witnesses.length === 0 && <div className="hint">None linked yet.</div>}
          {witnesses && witnesses.map((w) => (
            <div key={w.id} className="hint" style={{ marginTop: 4 }}>
              {w.name} {w.contact ? `— ${w.contact}` : ""}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function MattersTab({ caseId }) {
  const [matters, setMatters] = useState([]);
  const [error, setError] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [expandedId, setExpandedId] = useState(null);
  const [form, setForm] = useState({
    title: "", key_question: "", status: "under_investigation",
    description: "", location: "", matter_date: "",
  });

  function load() {
    api.listCaseMatters(caseId).then(setMatters).catch((e) => setError(e.message));
  }
  useEffect(load, [caseId]);

  async function createMatter(e) {
    e.preventDefault();
    setError(null);
    try {
      await api.createMatter({
        case_id: caseId,
        title: form.title,
        key_question: form.key_question || null,
        status: form.status,
        description: form.description || null,
        location: form.location || null,
        matter_date: form.matter_date ? new Date(form.matter_date).toISOString() : null,
      });
      setForm({ title: "", key_question: "", status: "under_investigation", description: "", location: "", matter_date: "" });
      setShowForm(false);
      load();
    } catch (err) { setError(err.message); }
  }

  return (
    <div>
      <div className="hint" style={{ marginBottom: 12 }}>
        Group everything tied to one real-world incident — a location, a date, a transaction — instead of a flat
        per-case document list. Click a matter to see every document, evidence item, and witness tied to it.
      </div>

      {error && <div className="error-banner">{error}</div>}

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <h3 style={{ margin: 0 }}>Key Matters in This Case</h3>
        <button className="btn" onClick={() => setShowForm((s) => !s)}>
          {showForm ? "Cancel" : "+ Add New Matter"}
        </button>
      </div>

      {showForm && (
        <div className="card" style={{ marginBottom: 14 }}>
          <form onSubmit={createMatter}>
            <label>Title</label>
            <input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })}
                   placeholder="e.g. Unauthorized entry into government warehouse" required />
            <label>Key Question</label>
            <input value={form.key_question} onChange={(e) => setForm({ ...form, key_question: e.target.value })}
                   placeholder="e.g. Was the accused present at the time of the theft?" />
            <label>Status</label>
            <select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>
              <option value="under_investigation">Under Investigation</option>
              <option value="evidence_collection">Evidence Collection</option>
              <option value="pending_review">Pending Review</option>
              <option value="closed">Closed</option>
            </select>
            <label>Location</label>
            <input value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })} placeholder="Optional" />
            <label>Date</label>
            <input type="date" value={form.matter_date} onChange={(e) => setForm({ ...form, matter_date: e.target.value })} />
            <label>Description</label>
            <input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} placeholder="Optional" />
            <button className="btn">Create Matter</button>
          </form>
        </div>
      )}

      {matters.map((m, i) => (
        <MatterCard
          key={m.id}
          matter={m}
          index={i}
          expanded={expandedId === m.id}
          onToggle={() => setExpandedId(expandedId === m.id ? null : m.id)}
          onStatusChanged={load}
        />
      ))}
      {matters.length === 0 && <div className="hint">No matters created for this case yet.</div>}
    </div>
  );
}
