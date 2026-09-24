import { useEffect, useState } from "react";
import { api } from "../api";

const NEXT_ACTIONS = {
  collected: [["seal", "Seal"]],
  sealed: [["transfer", "Transfer"]],
  transferred: [["receive", "Receive"]],
  received: [["examine", "Examine"]],
  examined: [["generate_report", "Generate Report"]],
  report_generated: [["use", "Mark Used in Prosecution/Court"]],
  used: [["archive", "Archive"]],
  archived: [],
};

export default function EvidenceTab({ caseId, documents }) {
  const [items, setItems] = useState([]);
  const [error, setError] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [matters, setMatters] = useState([]);
  const [form, setForm] = useState({ evidence_code: "", description: "", seizure_reference: "", linked_document_id: "", matter_id: "" });

  function load() {
    api.listEvidence(caseId).then(setItems).catch((e) => setError(e.message));
  }
  useEffect(() => {
    load();
    api.listCaseMatters(caseId).then(setMatters).catch(() => {});
  }, [caseId]);

  async function create(e) {
    e.preventDefault();
    setError(null);
    try {
      await api.createEvidence({
        case_id: caseId, ...form,
        linked_document_id: form.linked_document_id || null,
        matter_id: form.matter_id || null,
      });
      setForm({ evidence_code: "", description: "", seizure_reference: "", linked_document_id: "", matter_id: "" });
      setShowForm(false);
      load();
    } catch (err) { setError(err.message); }
  }

  async function assignMatter(ev, matterId) {
    setError(null);
    try {
      await api.assignEvidenceMatter(ev.id, matterId || null);
      load();
    } catch (err) { setError(err.message); }
  }

  async function transition(ev, action) {
    setError(null);
    try {
      await api.transitionEvidence(ev.id, { action });
      load();
    } catch (err) { setError(err.message); }
  }

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h3 style={{ margin: 0 }}>Evidence</h3>
        <button className="btn" onClick={() => setShowForm((s) => !s)}>{showForm ? "Cancel" : "+ New Evidence"}</button>
      </div>
      {error && <div className="error-banner">{error}</div>}

      {showForm && (
        <div className="card">
          <form onSubmit={create}>
            <label>Evidence Code</label>
            <input value={form.evidence_code} onChange={(e) => setForm({ ...form, evidence_code: e.target.value })} placeholder="E-002" required />
            <label>Description</label>
            <input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} required />
            <label>Seizure Reference</label>
            <input value={form.seizure_reference} onChange={(e) => setForm({ ...form, seizure_reference: e.target.value })} />
            <label>Linked Document (optional — e.g. forensic report)</label>
            <select value={form.linked_document_id} onChange={(e) => setForm({ ...form, linked_document_id: e.target.value })}>
              <option value="">— none —</option>
              {documents.map((d) => <option key={d.id} value={d.id}>{d.doc_ref} — {d.title}</option>)}
            </select>
            <label>Matter (event / incident this belongs to)</label>
            <select value={form.matter_id} onChange={(e) => setForm({ ...form, matter_id: e.target.value })}>
              <option value="">— none —</option>
              {matters.map((m) => <option key={m.id} value={m.id}>{m.title}</option>)}
            </select>
            <button className="btn">Register Evidence</button>
          </form>
        </div>
      )}

      <div className="card" style={{ padding: 0 }}>
        <table>
          <thead><tr><th>Code</th><th>Description</th><th>Status</th><th>Matter</th><th>Linked Doc</th><th>Actions</th></tr></thead>
          <tbody>
            {items.map((ev) => (
              <tr key={ev.id}>
                <td><strong>{ev.evidence_code}</strong></td>
                <td>{ev.description}</td>
                <td><span className="badge">{ev.status.replaceAll("_", " ")}</span></td>
                <td>
                  <select
                    value={ev.matter_id || ""}
                    onChange={(e) => assignMatter(ev, e.target.value)}
                    style={{ margin: 0, fontSize: 12 }}
                  >
                    <option value="">— none —</option>
                    {matters.map((m) => <option key={m.id} value={m.id}>{m.title}</option>)}
                  </select>
                </td>
                <td>{documents.find((d) => d.id === ev.linked_document_id)?.doc_ref || "—"}</td>
                <td>
                  {(NEXT_ACTIONS[ev.status] || []).map(([action, label]) => (
                    <button key={action} className="btn secondary" style={{ marginRight: 6 }}
                            onClick={() => transition(ev, action)}>{label}</button>
                  ))}
                </td>
              </tr>
            ))}
            {items.length === 0 && <tr><td colSpan={6} className="hint" style={{ padding: 14 }}>No evidence registered yet.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
