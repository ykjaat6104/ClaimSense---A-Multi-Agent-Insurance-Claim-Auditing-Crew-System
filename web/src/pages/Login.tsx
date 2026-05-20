import { FormEvent, useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { apiLogin, getToken, setToken } from "../api";

export default function Login() {
  const nav = useNavigate();
  const loc = useLocation() as { state?: { from?: string } };
  const [user, setUser] = useState("adjuster");
  const [pass, setPass] = useState("claimsense-demo");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (getToken()) {
    return <Navigate to={loc.state?.from || "/"} replace />;
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setErr(null);
    setBusy(true);
    try {
      const res = await apiLogin(user, pass);
      setToken(res.access_token);
      nav(loc.state?.from || "/", { replace: true });
    } catch (ex: unknown) {
      setErr(ex instanceof Error ? ex.message : "Login failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="sidebar-brand" style={{ border: "none", padding: "0 0 0.5rem", marginBottom: "0.5rem" }}>
          ClaimSense
        </div>
        <p className="page-sub" style={{ marginBottom: "1rem" }}>
          Adjuster workspace — sign in to run AI decision support on claims.
        </p>
        {err ? <div className="flash flash-err">{err}</div> : null}
        <form onSubmit={onSubmit}>
          <label>
            <span>Username</span>
            <input value={user} onChange={(e) => setUser(e.target.value)} autoComplete="username" />
          </label>
          <label>
            <span>Password</span>
            <input
              type="password"
              value={pass}
              onChange={(e) => setPass(e.target.value)}
              autoComplete="current-password"
            />
          </label>
          <button type="submit" className="btn-primary" disabled={busy} style={{ width: "100%", marginTop: "0.35rem" }}>
            {busy ? "Signing in…" : "Sign in"}
          </button>
          <p className="page-sub" style={{ marginTop: "1rem", fontSize: "0.82rem", marginBottom: 0 }}>
            Demo defaults match <code>.env.example</code> — rotate secrets in production.
          </p>
        </form>
      </div>
    </div>
  );
}
