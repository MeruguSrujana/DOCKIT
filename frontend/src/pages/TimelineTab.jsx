import { useEffect, useState } from "react";
import { api } from "../api";

export default function TimelineTab({ caseId, refreshKey }) {
  const [events, setEvents] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.timeline(caseId).then(setEvents).catch((e) => setError(e.message));
  }, [caseId, refreshKey]);

  return (
    <div className="card">
      <h3>Case Provenance Timeline</h3>
      <div className="hint" style={{ marginBottom: 14 }}>
        Rendered directly from the append-only event ledger — every entry below is a real recorded row, not assembled from current-state guesses.
      </div>
      {error && <div className="error-banner">{error}</div>}
      <div className="timeline">
        {events.map((e) => (
          <div key={e.id} className={`timeline-item ${e.event_type}`}>
            <div className="ev-type">
              {e.event_type.replaceAll("_", " ").toUpperCase()}
              {e.from_state && e.to_state && ` — ${e.from_state} → ${e.to_state}`}
            </div>
            <div className="ev-meta">
              {e.actor} · {new Date(e.timestamp).toLocaleString()}
              {e.destination && ` · to ${e.destination}`}
            </div>
            {e.details && <div className="ev-details">{e.details}</div>}
          </div>
        ))}
        {events.length === 0 && <div className="hint">No events recorded yet.</div>}
      </div>
    </div>
  );
}
