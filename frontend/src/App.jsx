import { BrowserRouter, Routes, Route, Navigate, useNavigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./AuthContext";
import Login from "./pages/Login";
import CaseList from "./pages/CaseList";
import CaseWorkspace from "./pages/CaseWorkspace";
import NotificationsBell from "./pages/NotificationsBell";
import SearchBar from "./pages/SearchBar";
import InboxPanel from "./pages/InboxPanel";

function Topbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  if (!user) return null;

  return (
    <div className="topbar">
      <div
        className="brand"
        onClick={() => navigate("/dashboard")}
        style={{ cursor: "pointer" }}
      >
        DOCKIT
      </div>

      <div style={{ display: "flex", alignItems: "center" }}>
        <SearchBar />

        <button className="link" onClick={() => navigate("/cases")}>
          Cases
        </button>

        <span className="who" style={{ marginLeft: 16 }}>
          {user.full_name} · {user.role.replaceAll("_", " ")}
        </span>

        <NotificationsBell />

        <button
          className="link"
          onClick={() => {
            logout();
            navigate("/login");
          }}
        >
          Sign out
        </button>
      </div>
    </div>
  );
}

function RequireAuth({ children }) {
  const { user, loading } = useAuth();

  if (loading) {
    return <div className="container hint">Loading...</div>;
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return children;
}

/* ---------------- DASHBOARD ----------------
 *
 * Role labels come from the backend in lower_snake_case
 * ("investigating_officer"), so they are matched in that form here.
 * Every role gets the same shell: their inbox (documents transferred
 * to them, awaiting acknowledgment) plus a way into the case list.
 * The blurb is the only per-role difference.
 */

const ROLE_INFO = {
  investigating_officer: {
    title: "Investigating Officer Dashboard",
    blurb: "Register cases, create FIRs and other documents, group them into matters, and transfer them onward.",
  },
  forensic_officer: {
    title: "Forensic Officer Dashboard",
    blurb: "Review evidence and documents transferred to you, and file forensic reports.",
  },
  prosecutor: {
    title: "Prosecutor Dashboard",
    blurb: "Review investigation and forensic documents, and raise disclosure requests for the defence.",
  },
  court_clerk: {
    title: "Court Dashboard",
    blurb: "View authorized case documents and manage court filings and disclosure requests.",
  },
  admin: {
    title: "Admin Dashboard",
    blurb: "Approve submissions, manage per-case access, and decide disclosure requests. Case content stays with the case officers.",
  },
  cyber_expert: {
    title: "Cyber Expert Dashboard",
    blurb: "Work on cases you have been granted access to by the Admin.",
  },
};

function Dashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  const info = ROLE_INFO[user.role] || {
    title: "Dashboard",
    blurb: `Your account role is: ${user.role}`,
  };

  return (
    <div className="container">
      <div className="hint">DOCKIT</div>
      <h1>{info.title}</h1>
      <p className="hint" style={{ marginTop: -6 }}>{info.blurb}</p>

      <div style={{ margin: "18px 0" }}>
        <button className="btn" onClick={() => navigate("/cases")}>
          Open Cases
        </button>
      </div>

      <InboxPanel />
    </div>
  );
}

/* ---------------- APPLICATION ---------------- */

function Shell() {
  return (
    <div className="app-shell">
      <Topbar />

      <Routes>
        <Route path="/login" element={<Login />} />

        <Route
          path="/dashboard"
          element={
            <RequireAuth>
              <Dashboard />
            </RequireAuth>
          }
        />

        <Route
          path="/cases"
          element={
            <RequireAuth>
              <CaseList />
            </RequireAuth>
          }
        />

        <Route
          path="/cases/:caseId"
          element={
            <RequireAuth>
              <CaseWorkspace />
            </RequireAuth>
          }
        />

        <Route
          path="*"
          element={<Navigate to="/dashboard" replace />}
        />
      </Routes>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Shell />
      </AuthProvider>
    </BrowserRouter>
  );
}
