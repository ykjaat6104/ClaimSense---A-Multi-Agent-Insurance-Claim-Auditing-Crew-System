import { FormEvent, useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { apiSignup, getToken, setToken } from "../api";

export default function Signup() {
  const nav = useNavigate();
  const [user, setUser] = useState("");
  const [name, setName] = useState("");
  const [pass, setPass] = useState("");
  const [confirm, setConfirm] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (getToken()) {
    return <Navigate to="/" replace />;
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setErr(null);

    if (pass !== confirm) {
      setErr("Passwords do not match");
      return;
    }
    if (pass.length < 6) {
      setErr("Password must be at least 6 characters");
      return;
    }
    if (user.length < 3) {
      setErr("Username must be at least 3 characters");
      return;
    }
    if (!name.trim()) {
      setErr("Display name is required");
      return;
    }

    setBusy(true);
    try {
      const res = await apiSignup(user, pass, name.trim());
      setToken(res.access_token);
      nav("/", { replace: true });
    } catch (ex: unknown) {
      setErr(ex instanceof Error ? ex.message : "Signup failed");
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
          Create an account to get started.
        </p>
        {err ? <div className="flash flash-err">{err}</div> : null}
        <form onSubmit={onSubmit}>
          <label>
            <span>Username</span>
            <input value={user} onChange={(e) => setUser(e.target.value)} autoComplete="username" />
          </label>
          <label>
            <span>Display Name</span>
            <input value={name} onChange={(e) => setName(e.target.value)} />
          </label>
          <label>
            <span>Password</span>
            <input
              type="password"
              value={pass}
              onChange={(e) => setPass(e.target.value)}
              autoComplete="new-password"
            />
          </label>
          <label>
            <span>Confirm Password</span>
            <input
              type="password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              autoComplete="new-password"
            />
          </label>
          <button type="submit" className="btn-primary" disabled={busy} style={{ width: "100%", marginTop: "0.35rem" }}>
            {busy ? "Creating account…" : "Create account"}
          </button>
        </form>
        <p className="page-sub" style={{ marginTop: "1rem", fontSize: "0.82rem", marginBottom: 0 }}>
          Already have an account? <Link to="/login">Sign in</Link>
        </p>
      </div>
    </div>
  );
}
