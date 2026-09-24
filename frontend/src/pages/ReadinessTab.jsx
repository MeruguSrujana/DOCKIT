import { useEffect, useState } from "react";
import { api } from "../api";

export default function ReadinessTab({ caseId, refreshKey }) {
  const [r, setR] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.readiness(caseId).then(setR).catch((e) => setError(e.message));
  }, [caseId, refreshKey]);

  if (error) return <div className="error-banner">{error}</div>;
  if (!r) return <div className="hint">Loading...</div>;

  return (
    <div>
      <div className="card">
        <h3>Documentary Readiness</h3>
        <div className="hint">Rule-based, computed live from persisted case/document/event state — not a predictive or AI-generated score.</div>
        <div style={{ marginTop: 14 }}>
          <strong>{r.completeness_pct}%</strong> of registered documents approved
        </div>
        <div className="readiness-bar-track">
          <div className="readiness-bar-fill" style={{ width: `${r.completeness_pct}%` }} />
        </div>

        <div className="grid3" style={{ marginTop: 10 }}>
          <div className="stat"><div className="num">{r.total_documents}</div><div className="label">Documents</div></div>
          <div className="stat"><div className="num">{r.pending_review}</div><div className="label">Pending Review</div></div>
          <div className="stat"><div className="num">{r.integrity_failures}</div><div className="label">Integrity Failures</div></div>
        </div>

        <div style={{ marginTop: 16 }}>
          <strong>Checklist</strong>
          <ul>
            {Object.entries(r.checklist).map(([type, present]) => (
              <li key={type}>
                {present ? "✓" : "✕"} {type.replaceAll("_", " ")}
              </li>
            ))}
          </ul>
        </div>

        <div style={{ marginTop: 12 }}>
          <strong>Next required action: </strong>
          {r.next_required_action || "None — case is documentarily up to date."}
        </div>
        {r.last_activity && (
          <div className="hint" style={{ marginTop: 8 }}>
            Last activity: {new Date(r.last_activity).toLocaleString()}
          </div>
        )}
      </div>
    </div>
  );
}
