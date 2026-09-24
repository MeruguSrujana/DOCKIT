import { useEffect, useState } from "react";
import { api } from "../api";

const PARTY_ROLES = ["complainant", "accused", "witness", "advocate", "other"];

export default function PeopleTab({ caseId }) {
  const [parties, setParties] = useState([]);
  const [notes, setNotes] = useState([]);
  const [matters, setMatters] = useState([]);
  const [error, setError] = useState(null);

  const [showPartyForm, setShowPartyForm] = useState(false);
  const [partyForm, setPartyForm] = useState({ party_role: "complainant", name: "", contact: "", notes: "", matter_id: "" });

  const [noteText, setNoteText] = useState("");
  const [notePinned, setNotePinned] = useState(false);

  function load() {
    api.listCaseParties(caseId).then(setParties).catch((e) => setError(e.message));
    api.listCaseNotes(caseId).then(setNotes).catch((e) => setError(e.message));
    api.listCaseMatters(caseId).then(setMatters).catch((e) => setError(e.message));
  }
  useEffect(load, [caseId]);

  function matterTitle(id) {
    if (!id) return "—";
    const m = matters.find((x) => x.id === id);
    return m ? m.title : "—";
  }

  async function addParty(e) {
    e.preventDefault();
    setError(null);
    try {
      await api.createParty({ case_id: caseId, ...partyForm, matter_id: partyForm.matter_id || null });
      setPartyForm({ party_role: "complainant", name: "", contact: "", notes: "", matter_id: "" });
      setShowPartyForm(false);
      load();
    } catch (err) { setError(err.message); }
  }

  async function addNote(e) {
    e.preventDefault();
    if (!noteText.trim()) return;
    setError(null);
    try {
      await api.createNote({ case_id: caseId, content: noteText, pinned: notePinned });
      setNoteText("");
      setNotePinned(false);
      load();
    } catch (err) { setError(err.message); }
  }

  return (
    <div>
      {error && <div className="error-banner">{error}</div>}

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h3 style={{ margin: 0 }}>Parties</h3>
        <button className="btn" onClick={() => setShowPartyForm((s) => !s)}>
          {showPartyForm ? "Cancel" : "+ Add Party"}
        </button>
      </div>

      {showPartyForm && (
        <div className="card">
          <form onSubmit={addParty}>
            <label>Role</label>
            <select value={partyForm.party_role} onChange={(e) => setPartyForm({ ...partyForm, party_role: e.target.value })}>
              {PARTY_ROLES.map((r) => <option key={r} value={r}>{r.replaceAll("_", " ")}</option>)}
            </select>
            <label>Linked matter</label>
            <select value={partyForm.matter_id} onChange={(e) => setPartyForm({ ...partyForm, matter_id: e.target.value })}>
              <option value="">— None —</option>
              {matters.map((m) => <option key={m.id} value={m.id}>{m.title}</option>)}
            </select>
            <label>Name</label>
            <input value={partyForm.name} onChange={(e) => setPartyForm({ ...partyForm, name: e.target.value })} required />
            <label>Contact</label>
            <input value={partyForm.contact} onChange={(e) => setPartyForm({ ...partyForm, contact: e.target.value })} placeholder="Phone / address (optional)" />
            <label>Notes</label>
            <input value={partyForm.notes} onChange={(e) => setPartyForm({ ...partyForm, notes: e.target.value })} placeholder="Optional" />
            <button className="btn">Add Party</button>
          </form>
        </div>
      )}

      <div className="card" style={{ padding: 0 }}>
        <table>
          <thead><tr><th>Role</th><th>Name</th><th>Matter</th><th>Contact</th><th>Notes</th></tr></thead>
          <tbody>
            {parties.map((p) => (
              <tr key={p.id}>
                <td><span className="badge">{p.party_role.replaceAll("_", " ")}</span></td>
                <td><strong>{p.name}</strong></td>
                <td>{matterTitle(p.matter_id)}</td>
                <td>{p.contact || "—"}</td>
                <td>{p.notes || "—"}</td>
              </tr>
            ))}
            {parties.length === 0 && <tr><td colSpan={5} className="hint" style={{ padding: 14 }}>No parties added yet.</td></tr>}
          </tbody>
        </table>
      </div>

      <h3 style={{ marginTop: 28 }}>Case Notes</h3>

      <div className="card">
        <form onSubmit={addNote}>
          <label>Add a note</label>
          <textarea rows={3} value={noteText} onChange={(e) => setNoteText(e.target.value)} placeholder="Investigative note or observation..." required />
          <label style={{ display: "flex", alignItems: "center", gap: 6, fontWeight: 400 }}>
            <input type="checkbox" style={{ width: "auto", margin: 0 }} checked={notePinned}
                   onChange={(e) => setNotePinned(e.target.checked)} />
            Pin this note
          </label>
          <button className="btn" style={{ marginTop: 8 }}>Add Note</button>
        </form>
      </div>

      {notes.map((n) => (
        <div key={n.id} className="card" style={{ marginBottom: 10 }}>
          {n.pinned && <span className="badge" style={{ marginBottom: 6 }}>Pinned</span>}
          <div>{n.content}</div>
          <div className="hint" style={{ marginTop: 8 }}>
            {n.author_name} · {new Date(n.created_at).toLocaleString()}
          </div>
        </div>
      ))}
      {notes.length === 0 && <div className="hint">No notes yet.</div>}
    </div>
  );
}
