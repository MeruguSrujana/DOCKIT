import { useEffect, useState } from "react";
import { api } from "../api";

export default function CaseManagePanel({ caseObj, onChanged }) {
  const [open, setOpen] = useState(false);
  const [users, setUsers] = useState([]);
  const [error, setError] = useState(null);

  const [ownerId, setOwnerId] = useState(caseObj.owner_id || "");
  const [retentionDate, setRetentionDate] = useState(
    caseObj.retention_date ? caseObj.retention_date.slice(0, 10) : ""
  );

  useEffect(() => {
    if (open) api.listUsers().then(setUsers).catch(() => {});
  }, [open]);

  async function saveOwner(e) {
    e.preventDefault();
    setError(null);
    try {
      await api.assignCaseOwner(caseObj.id, ownerId);
      onChanged();
    } catch (err) { setError(err.message); }
  }

  async function saveRetention(e) {
    e.preventDefault();
    setError(null);
    try {
      await api.setCaseRetention(caseObj.id, new Date(retentionDate).toISOString());
      onChanged();
    } catch (err) { setError(err.message); }
  }

  async function toggleActive() {
    setError(null);
    try {
      await api.setCaseActiveStatus(caseObj.id, !caseObj.is_active);
      onChanged();
    } catch (err) { setError(err.message); }
  }

  async function dispose(status) {
    setError(null);
    try {
      await api.disposeCase(caseObj.id, status);
      onChanged();
    } catch (err) { setError(err.message); }
  }

  return (
    <div style={{ marginBottom: 18 }}>
      <button className="btn secondary" onClick={() => setOpen((o) => !o)}>
        {open ? "Hide Case Settings" : "Case Settings"}
      </button>

      {open && (
        <div className="card" style={{ marginTop: 10 }}>
          {error && <div className="error-banner">{error}</div>}

          <div className="grid3">
            <div>
              <form onSubmit={saveOwner}>
                <label>Case Owner</label>
                <select value={ownerId} onChange={(e) => setOwnerId(e.target.value)}>
                  <option value="">— unassigned —</option>
                  {users.map((u) => <option key={u.id} value={u.id}>{u.full_name}</option>)}
                </select>
                <button className="btn secondary" style={{ width: "100%" }}>Save Owner</button>
              </form>
            </div>

            <div>
              <form onSubmit={saveRetention}>
                <label>Retention Date</label>
                <input type="date" value={retentionDate} onChange={(e) => setRetentionDate(e.target.value)} />
                <button className="btn secondary" style={{ width: "100%" }} disabled={!retentionDate}>Set Retention</button>
              </form>
            </div>

            <div>
              <label>Case Status</label>
              <div className="hint" style={{ marginBottom: 8 }}>
                {caseObj.is_active ? "Active" : "Closed"} · {caseObj.disposal_status.replaceAll("_", " ")}
                {caseObj.legal_hold && <> · <strong>Legal Hold</strong></>}
              </div>
              <button className="btn secondary" style={{ width: "100%", marginBottom: 8 }} onClick={toggleActive}>
                {caseObj.is_active ? "Close Case" : "Reactivate Case"}
              </button>
              {caseObj.disposal_status === "active" && (
                <button className="btn secondary" style={{ width: "100%" }} onClick={() => dispose("pending_disposal")}>
                  Mark for Disposal
                </button>
              )}
              {caseObj.disposal_status === "pending_disposal" && (
                <button className="btn danger" style={{ width: "100%" }} onClick={() => dispose("disposed")}>
                  Confirm Disposal
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
