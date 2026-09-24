import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";

/**
 * Cross-case list of documents currently held by the logged-in user with
 * status "transferred" — i.e. genuinely handed over and awaiting their
 * acknowledgment. This is what makes the transfer flow visible to the
 * receiving officer: before this, a Forensic Officer had no signal that
 * a document was waiting on them.
 */
export default function InboxPanel() {
  const [items, setItems] = useState([]);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  function load() {
    api.listInbox().then(setItems).catch((e) => setError(e.message));
  }

  useEffect(() => {
    load();
    const t = setInterval(load, 30000);
    return () => clearInterval(t);
  }, []);

  return (
    <div className="card">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h3 style={{ margin: 0 }}>
          My Inbox{items.length > 0 ? ` (${items.length})` : ""}
        </h3>
        <button className="btn secondary" onClick={load}>Refresh</button>
      </div>

      <div className="hint" style={{ marginTop: 6, marginBottom: 10 }}>
        Documents transferred to you and awaiting your acknowledgment. Open one to view it and acknowledge receipt.
      </div>

      {error && <div className="error-banner">{error}</div>}

      {items.length === 0 && <div className="hint">Nothing waiting on you right now.</div>}

      {items.map((d) => (
        <div
          key={d.id}
          onClick={() => navigate(`/cases/${d.case_id}?openDoc=${d.id}`)}
          style={{
            padding: "10px 12px", border: "1px solid #EEE", borderRadius: 6,
            marginBottom: 8, cursor: "pointer", background: "var(--accent-tint)",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between" }}>
            <strong>{d.doc_ref}</strong>
            <span className="badge">{d.status}</span>
          </div>
          <div style={{ marginTop: 4 }}>{d.title}</div>
          <div className="hint" style={{ marginTop: 4 }}>
            {d.doc_type.replaceAll("_", " ")} · Case {d.case_number}
          </div>
        </div>
      ))}
    </div>
  );
}
