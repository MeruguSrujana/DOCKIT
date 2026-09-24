import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";

export default function SearchBar() {
  const [q, setQ] = useState("");
  const [results, setResults] = useState(null);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const boxRef = useRef(null);
  const navigate = useNavigate();

  // Debounced live search — fires as you type, no button press needed.
  useEffect(() => {
    if (q.trim().length < 1) {
      setResults(null);
      return;
    }
    setLoading(true);
    const t = setTimeout(() => {
      api.search(q)
        .then((r) => { setResults(r); setOpen(true); })
        .catch(() => setResults(null))
        .finally(() => setLoading(false));
    }, 250);
    return () => clearTimeout(t);
  }, [q]);

  // Close when clicking outside.
  useEffect(() => {
    function onClick(e) {
      if (boxRef.current && !boxRef.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  function go(caseId) {
    setOpen(false);
    setQ("");
    navigate(`/cases/${caseId}`);
  }

  const groups = results
    ? [
        { label: "Cases", items: results.cases, render: (c) => `${c.case_number} · ${c.status}`, caseId: (c) => c.id },
        { label: "Documents", items: results.documents, render: (d) => `${d.doc_ref} — ${d.title}`, caseId: (d) => d.case_id },
        { label: "Evidence", items: results.evidence, render: (e) => `${e.evidence_code} — ${e.description}`, caseId: (e) => e.case_id },
        { label: "People", items: results.parties, render: (p) => `${p.name} (${p.party_role})`, caseId: (p) => p.case_id },
        { label: "Matters", items: results.matters, render: (m) => m.title, caseId: (m) => m.case_id },
        { label: "Notes", items: results.notes, render: (n) => n.content, caseId: (n) => n.case_id },
      ].filter((g) => g.items && g.items.length > 0)
    : [];

  const totalHits = groups.reduce((sum, g) => sum + g.items.length, 0);

  return (
    <span ref={boxRef} style={{ position: "relative", marginRight: 16 }}>
      <input
        value={q}
        onChange={(e) => setQ(e.target.value)}
        onFocus={() => results && setOpen(true)}
        placeholder="Search cases, documents, people..."
        style={{
          width: 260, padding: "6px 10px", fontSize: 13, borderRadius: 5,
          border: "1px solid rgba(255,255,255,0.35)", background: "rgba(255,255,255,0.12)",
          color: "white", outline: "none", margin: 0,
        }}
      />

      {open && (
        <div
          style={{
            position: "absolute", left: 0, top: "100%", marginTop: 6, width: 380,
            background: "white", color: "var(--black)", border: "1px solid #DDD",
            borderRadius: 6, boxShadow: "0 6px 18px rgba(0,0,0,0.15)", zIndex: 30,
            maxHeight: 420, overflowY: "auto",
          }}
        >
          {loading && <div className="hint" style={{ padding: 12 }}>Searching...</div>}
          {!loading && totalHits === 0 && <div className="hint" style={{ padding: 12 }}>No matches for "{q}".</div>}

          {groups.map((g) => (
            <div key={g.label}>
              <div style={{ padding: "8px 12px 4px", fontSize: 11, fontWeight: 700, color: "#888", textTransform: "uppercase" }}>
                {g.label}
              </div>
              {g.items.map((item) => (
                <div
                  key={item.id}
                  onClick={() => go(g.caseId(item))}
                  style={{ padding: "8px 12px", borderBottom: "1px solid #F2F2F2", cursor: "pointer", fontSize: 12.5 }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = "var(--accent-tint)")}
                  onMouseLeave={(e) => (e.currentTarget.style.background = "white")}
                >
                  {g.render(item)}
                </div>
              ))}
            </div>
          ))}
        </div>
      )}
    </span>
  );
}
