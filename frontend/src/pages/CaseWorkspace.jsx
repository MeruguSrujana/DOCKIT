import { useEffect, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../AuthContext";
import ReadinessTab from "./ReadinessTab";
import DocumentsTab from "./DocumentsTab";
import EvidenceTab from "./EvidenceTab";
import TimelineTab from "./TimelineTab";
import PeopleTab from "./PeopleTab";
import TasksTab from "./TasksTab";
import MattersTab from "./MattersTab";
import CaseManagePanel from "./CaseManagePanel";
import AdminTab from "./AdminTab";

const BASE_TABS = ["Overview", "Documents", "Matters", "Evidence", "Timeline", "People", "Tasks"];

export default function CaseWorkspace() {
  const { caseId } = useParams();
  const { user } = useAuth();
  const [searchParams] = useSearchParams();
  const openDocId = searchParams.get("openDoc");
  const [caseObj, setCaseObj] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [tab, setTab] = useState(openDocId ? "Documents" : "Overview");
  const [refreshKey, setRefreshKey] = useState(0);
  const [error, setError] = useState(null);

  const TABS = user?.role === "admin" ? [...BASE_TABS, "Admin"] : BASE_TABS;

  function bump() { setRefreshKey((k) => k + 1); }
  function reloadCase() { api.getCase(caseId).then(setCaseObj).catch((e) => setError(e.message)); }

  useEffect(reloadCase, [caseId]);

  useEffect(() => {
    api.listDocuments(caseId).then(setDocuments).catch(() => {});
  }, [caseId, refreshKey]);

  if (error) return <div className="container"><div className="error-banner">{error}</div></div>;
  if (!caseObj) return <div className="container hint">Loading case...</div>;

  return (
    <div className="container">
      <div className="hint">CASE WORKSPACE</div>
      <h2>{caseObj.case_number}</h2>
      <div style={{ marginBottom: 16 }}>
        <span className="badge">{caseObj.case_type.replaceAll("_", " ")}</span>{" "}
        <span className="badge">{caseObj.status}</span>{" "}
        {caseObj.jurisdiction && <span className="badge">{caseObj.jurisdiction}</span>}{" "}
        {caseObj.priority && <span className="badge">{caseObj.priority} priority</span>}{" "}
        {caseObj.legal_hold && <span className="badge" style={{ background: "#FBE8E6", color: "#A3453D" }}>Legal Hold</span>}
        {caseObj.is_restricted && <span className="badge" style={{ background: "#FBE8E6", color: "#A3453D" }}>Restricted</span>}
      </div>

      <CaseManagePanel caseObj={caseObj} onChanged={() => { bump(); reloadCase(); }} />

      <div className="tabs">
        {TABS.map((t) => (
          <button key={t} className={tab === t ? "active" : ""} onClick={() => setTab(t)}>{t}</button>
        ))}
      </div>

      {tab === "Overview" && <ReadinessTab caseId={caseId} refreshKey={refreshKey} />}
      {tab === "Documents" && <DocumentsTab caseId={caseId} onChanged={bump} autoOpenDocId={openDocId} />}
      {tab === "Matters" && <MattersTab caseId={caseId} />}
      {tab === "Evidence" && <EvidenceTab caseId={caseId} documents={documents} />}
      {tab === "Timeline" && <TimelineTab caseId={caseId} refreshKey={refreshKey} />}
      {tab === "People" && <PeopleTab caseId={caseId} />}
      {tab === "Tasks" && <TasksTab caseId={caseId} />}
      {tab === "Admin" && user?.role === "admin" && (
        <AdminTab caseId={caseId} caseObj={caseObj} onCaseChanged={reloadCase} />
      )}
    </div>
  );
}
