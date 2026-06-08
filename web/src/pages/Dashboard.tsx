import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { listClaims } from "../api";

type Row = {
  id: string;
  status: string;
  decision: string | null;
  risk_score: number | null;
  fraud_probability: number | null;
  created_at: string | null;
};

function riskDot(score: number | null) {
  if (score == null) return "dot dot-mid";
  if (score < 35) return "dot dot-low";
  if (score < 65) return "dot dot-mid";
  return "dot dot-high";
}

function MiniSpark() {
  return (
    <svg className="spark" viewBox="0 0 72 28" preserveAspectRatio="none">
      <polyline
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        points="0,22 12,18 24,20 36,10 48,14 60,6 72,12"
      />
    </svg>
  );
}

export default function Dashboard() {
  const [rows, setRows] = useState<Row[]>([]);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let on = true;
    (async () => {
      try {
        const data = await listClaims();
        if (on) setRows(data);
      } catch (e: unknown) {
        if (on) setErr(e instanceof Error ? e.message : "Load failed");
      }
    })();
    return () => {
      on = false;
    };
  }, []);

  const stats = useMemo(() => {
    const done = rows.filter((r) => r.status === "completed" && r.risk_score != null);
    const avgRisk =
      done.length > 0 ? Math.round(done.reduce((a, r) => a + (r.risk_score || 0), 0) / done.length) : null;
    const avgFraud =
      done.length > 0
        ? Math.round(done.reduce((a, r) => a + (r.fraud_probability || 0), 0) / done.length)
        : null;
    const last = rows[0];
    return { avgRisk, avgFraud, last, n: rows.length, completed: done.length };
  }, [rows]);

  const heroScore = stats.avgRisk != null ? (stats.avgRisk / 10).toFixed(1) : "—";
  const rec =
    stats.avgRisk == null
      ? "Upload and run claims to populate portfolio risk signals."
      : stats.avgRisk >= 65
        ? "Elevated portfolio risk — prioritize manual review on open claims."
        : stats.avgRisk >= 40
          ? "Mixed signals — validate policy fit and invoice anomalies on recent files."
          : "Portfolio risk within tolerance — continue spot checks on high-value claims.";

  const tier = (label: string, val: string, cls: string) => (
    <div className={`risk-tier ${cls}`}>
      <span>{label}</span>
      <strong>{val}</strong>
    </div>
  );

  const navTasks = [
    {
      tab: "Dashboard",
      work: "Portfolio overview, live queue snapshot, and risk posture.",
      action: "Open recent claims or start a new evaluation.",
    },
    {
      tab: "Claims Mgmt.",
      work: "Upload claim, invoice, policy, evidence, and extra docs, then run the multi-agent pipeline.",
      action: "Choose files, upload, process, and jump to results.",
    },
    {
      tab: "Results",
      work: "Browse completed evaluations and export reports as PDF, JSON, or DOCX.",
      action: "Open a claim report or export from the list.",
    },
    {
      tab: "Reports",
      work: "Search historical claims, compare cases, and open claim reports.",
      action: "Filter by claim ID, compare selected cases, and open report details.",
    },
    {
      tab: "Result dashboard",
      work: "Review agent output, approve/reject/manual-review per claim.",
      action: "Use the action buttons after a claim finishes processing.",
      contextual: true,
    },
  ];

  return (
    <div>
      <h1 className="page-title">Dashboard</h1>
      <p className="page-sub">AI threat & risk posture across your evaluated claims (decision support).</p>
      {err ? <div className="flash flash-err">{err}</div> : null}

      <div className="grid-hero">
        <div className="card card-hero-ai">
          <h2 style={{ color: "#fff", marginBottom: "0.5rem" }}>AI claim & fraud analysis summary</h2>
          <div style={{ display: "flex", alignItems: "baseline", gap: "0.75rem", flexWrap: "wrap" }}>
            <span className="hero-score">{heroScore}</span>
            <span style={{ color: "var(--muted)", fontSize: "1rem" }}>/ 10 portfolio risk</span>
          </div>
          <p className="hero-rec">{rec}</p>
          <div style={{ marginTop: "1rem" }}>
            <Link to="/claims-mgmt" className="btn-yellow" style={{ display: "inline-block", padding: "0.55rem 1.2rem", borderRadius: "10px", textDecoration: "none", color: "#0d0d0d", fontWeight: 700 }}>
              New claim evaluation
            </Link>
          </div>
        </div>

        <div className="card">
          <h2>Queue snapshot</h2>
          <div className="score-row">
            <div className="score-block">
              <span>Total submissions</span>
              <strong>{stats.n}</strong>
            </div>
            <div className="score-block">
              <span>Completed analyses</span>
              <strong>{stats.completed}</strong>
            </div>
          </div>
          <p className="page-sub" style={{ margin: "0.75rem 0 0", fontSize: "0.85rem" }}>
            Avg. fraud probability:{" "}
            <strong style={{ color: "var(--yellow)" }}>{stats.avgFraud != null ? `${stats.avgFraud}%` : "—"}</strong>
          </p>
        </div>
      </div>

      <div className="card" style={{ marginBottom: "1rem" }}>
        <h2>Tab guide for the multi-agent workflow</h2>
        <p className="page-sub" style={{ marginTop: 0 }}>
          These are the tabs that currently do real work. The removed roadmap tabs were placeholders for future modules.
        </p>
        <table className="data">
          <thead>
            <tr>
              <th>Tab</th>
              <th>What it does</th>
              <th>Buttons / actions</th>
            </tr>
          </thead>
          <tbody>
            {navTasks.map((item) => (
              <tr key={item.tab}>
                <td>
                  <strong>{item.tab}</strong>
                  {item.contextual ? <div className="page-sub" style={{ margin: 0 }}>Contextual page, not in sidebar</div> : null}
                </td>
                <td>{item.work}</td>
                <td>{item.action}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card" style={{ marginBottom: "1rem" }}>
        <h2>Risk lens (illustrative buckets)</h2>
        <div className="risk-strip">
          {tier("Coverage fit", stats.avgRisk != null ? `${Math.max(0, 100 - stats.avgRisk)}%` : "—", "tier-vl")}
          {tier("Invoice", stats.avgRisk != null ? `${Math.min(100, stats.avgRisk + 8)}%` : "—", "tier-l")}
          {tier("Timing", stats.avgRisk != null ? `${Math.min(100, stats.avgRisk)}%` : "—", "tier-m")}
          {tier("Documents", stats.avgRisk != null ? `${Math.min(100, stats.avgRisk + 15)}%` : "—", "tier-mh")}
          {tier("CAT exposure", "—", "tier-h")}
        </div>
      </div>

      <div className="card">
        <h2>Recent claims</h2>
        <table className="data">
          <thead>
            <tr>
              <th>Claim ID</th>
              <th>Status</th>
              <th>Risk</th>
              <th>AI decision</th>
              <th>Trend</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {rows.slice(0, 12).map((r) => (
              <tr key={r.id}>
                <td>
                  <span className={riskDot(r.risk_score)} />
                  <Link to={`/results/${r.id}`}>{r.id.slice(0, 8)}…</Link>
                </td>
                <td>{r.status}</td>
                <td>{r.risk_score ?? "—"}</td>
                <td>
                  <span
                    className={
                      "pill pill-" +
                      (r.decision === "APPROVE" ? "approve" : r.decision === "REJECT" ? "reject" : "review")
                    }
                  >
                    {(r.decision || "—").toString()}
                  </span>
                </td>
                <td>
                  <MiniSpark />
                </td>
                <td style={{ textAlign: "right" }}>
                  <Link to={`/results/${r.id}`}>Open</Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!rows.length ? <p className="page-sub">No claims yet — start from Claims Mgmt.</p> : null}
      </div>
    </div>
  );
}
