import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../AuthContext";

export default function CaseList() {
  const [cases, setCases] = useState([]);
  const [error, setError] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [caseNumber, setCaseNumber] = useState("");
  const [caseType, setCaseType] = useState("crime_against_women");
  const [priority, setPriority] = useState("medium");
  const [source, setSource] = useState("walk_in");

  // Jurisdiction: District -> Mandal -> Police Station / Revenue Office
  const [districts, setDistricts] = useState([]);
  const [mandals, setMandals] = useState([]);
  const [policeStations, setPoliceStations] = useState([]);
  const [revenueOffices, setRevenueOffices] = useState([]);
  const [district, setDistrict] = useState("");
  const [mandal, setMandal] = useState("");
  const [policeStation, setPoliceStation] = useState("");
  const [revenueOffice, setRevenueOffice] = useState("");

  const LAND_REVENUE_TYPES = ["land_dispute", "revenue_dispute"];
  const needsRevenueOffice = LAND_REVENUE_TYPES.includes(caseType);
  const { user } = useAuth();
  const navigate = useNavigate();

  const canCreate = user && ["investigating_officer", "admin"].includes(user.role);

  function load() {
    api.listCases().then(setCases).catch((e) => setError(e.message));
  }

  useEffect(load, []);
  useEffect(() => {
    api.listDistricts().then(setDistricts).catch(() => {});
  }, []);
  useEffect(() => {
    setMandal(""); setPoliceStation(""); setRevenueOffice("");
    setPoliceStations([]); setRevenueOffices([]);
    if (district) {
      api.listMandals(district).then(setMandals).catch(() => setMandals([]));
    } else {
      setMandals([]);
    }
  }, [district]);
  useEffect(() => {
    setPoliceStation(""); setRevenueOffice("");
    if (district && mandal) {
      api.listPoliceStations(district, mandal).then(setPoliceStations).catch(() => setPoliceStations([]));
      api.listRevenueOffices(district, mandal).then(setRevenueOffices).catch(() => setRevenueOffices([]));
    } else {
      setPoliceStations([]); setRevenueOffices([]);
    }
  }, [district, mandal]);

  async function submit(e) {
    e.preventDefault();
    setError(null);
    try {
      await api.createCase({
        case_number: caseNumber, case_type: caseType,
        district, mandal, police_station: policeStation, revenue_office: revenueOffice,
        priority, source,
      });
      setCaseNumber(""); setPriority("medium"); setSource("walk_in"); setShowForm(false);
      setDistrict(""); setMandal(""); setPoliceStation(""); setRevenueOffice("");
      load();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="container">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h2>Cases</h2>
        {canCreate && (
          <button className="btn" onClick={() => setShowForm((s) => !s)}>
            {showForm ? "Cancel" : "+ New Case"}
          </button>
        )}
      </div>

      {error && <div className="error-banner">{error}</div>}

      {showForm && (
        <div className="card">
          <form onSubmit={submit}>
            <label>Case Number</label>
            <input value={caseNumber} onChange={(e) => setCaseNumber(e.target.value)} placeholder="CASE-2026-021" required />
            <label>Case Type</label>
            <select value={caseType} onChange={(e) => setCaseType(e.target.value)}>
              <option value="crime_against_women">Crime Against Women</option>
              <option value="cyber_crime">Cyber Crime</option>
              <option value="road_accident">Road Accident</option>
              <option value="property_offence">Property Offence</option>
              <option value="land_dispute">Land Dispute</option>
              <option value="revenue_dispute">Revenue Dispute</option>
              <option value="other">Other</option>
            </select>
            <label>Jurisdiction</label>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <div style={{ flex: "1 1 150px" }}>
                <div className="hint" style={{ fontSize: 11 }}>District</div>
                <input list="district-options" value={district} onChange={(e) => setDistrict(e.target.value)} placeholder="Type to search..." />
                <datalist id="district-options">
                  {districts.map((d) => <option key={d} value={d} />)}
                </datalist>
              </div>
              <div style={{ flex: "1 1 150px" }}>
                <div className="hint" style={{ fontSize: 11 }}>Mandal</div>
                <input list="mandal-options" value={mandal} onChange={(e) => setMandal(e.target.value)}
                       disabled={!district} placeholder={district ? "Type to search..." : "Pick a district first"} />
                <datalist id="mandal-options">
                  {mandals.map((m) => <option key={m} value={m} />)}
                </datalist>
              </div>
              <div style={{ flex: "1 1 170px" }}>
                <div className="hint" style={{ fontSize: 11 }}>
                  Police Station {!needsRevenueOffice && "(required)"}
                </div>
                <input list="ps-options" value={policeStation} onChange={(e) => setPoliceStation(e.target.value)}
                       disabled={!mandal} placeholder={mandal ? "Type to search..." : "Pick a mandal first"} />
                <datalist id="ps-options">
                  {policeStations.map((p) => <option key={p} value={p} />)}
                </datalist>
              </div>
              <div style={{ flex: "1 1 170px" }}>
                <div className="hint" style={{ fontSize: 11 }}>
                  Revenue Office {needsRevenueOffice && "(required)"}
                </div>
                <input list="ro-options" value={revenueOffice} onChange={(e) => setRevenueOffice(e.target.value)}
                       disabled={!mandal} placeholder={mandal ? "Type to search..." : "Pick a mandal first"} />
                <datalist id="ro-options">
                  {revenueOffices.map((r) => <option key={r} value={r} />)}
                </datalist>
              </div>
            </div>
            <label>Priority</label>
            <select value={priority} onChange={(e) => setPriority(e.target.value)}>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="critical">Critical</option>
            </select>
            <label>Source</label>
            <select value={source} onChange={(e) => setSource(e.target.value)}>
              <option value="walk_in">Walk-in</option>
              <option value="e_fir">e-FIR</option>
              <option value="zero_fir">Zero FIR</option>
              <option value="referral">Referral</option>
              <option value="other">Other</option>
            </select>
            <button className="btn">Create Case</button>
          </form>
        </div>
      )}

      <div className="card" style={{ padding: 0 }}>
        <table>
          <thead>
            <tr><th>Case No.</th><th>Type</th><th>Jurisdiction</th><th>Priority</th><th>Status</th><th>Created</th></tr>
          </thead>
          <tbody>
            {cases.map((c) => (
              <tr key={c.id} style={{ cursor: "pointer" }} onClick={() => navigate(`/cases/${c.id}`)}>
                <td><strong>{c.case_number}</strong></td>
                <td>{c.case_type.replaceAll("_", " ")}</td>
                <td>
                  {c.district ? `${c.district} \u2192 ${c.mandal || "—"}` : (c.jurisdiction || "—")}
                </td>
                <td><span className="badge">{c.priority || "medium"}</span></td>
                <td><span className="badge">{c.status}</span></td>
                <td>{new Date(c.created_at).toLocaleDateString()}</td>
              </tr>
            ))}
            {cases.length === 0 && (
              <tr><td colSpan={6} className="hint" style={{ padding: 16 }}>No cases yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
