import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../AuthContext";

const DEMO_USERS = [
  ["io.sharma", "Investigating Officer"],
  ["fo.rao", "Forensic Officer"],
  ["pp.iyer", "Prosecutor"],
  ["cc.das", "Court Clerk"],
  ["admin", "Admin"],
];

export default function Login() {
  const [username, setUsername] = useState("io.sharma");
  const [password, setPassword] = useState("Dockit@2026");
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(username, password);
      navigate("/cases");
    } catch (err) {
      setError(err.message || "Login failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-wrap">
      <div className="login-card">
        <h2 className="login-title">DOCKIT</h2>
        <div className="login-sub">SIH26190 · Case-Centric Document Lifecycle System</div>
        {error && <div className="error-banner">{error}</div>}
        <form onSubmit={submit}>
          <label>Username</label>
          <input value={username} onChange={(e) => setUsername(e.target.value)} />
          <label>Password</label>
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
          <button className="btn" style={{ width: "100%" }} disabled={busy}>
            {busy ? "Signing in..." : "Sign in"}
          </button>
        </form>
        <div className="hint" style={{ marginTop: 16 }}>
          Demo accounts (password: Dockit@2026):
          <ul style={{ paddingLeft: 18, margin: "6px 0 0" }}>
            {DEMO_USERS.map(([u, label]) => (
              <li key={u}>{u} — {label}</li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
