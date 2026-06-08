import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { BarChart, Bar, PieChart, Pie, Cell, ResponsiveContainer, XAxis, YAxis, Tooltip } from "recharts";
import { adjusterAction, getReport } from "../api";

type Report = {
  id: string;
  status: string;
  decision: string | null;
  risk_score: number | null;
  fraud_probability: number | null;
  flags: string[];
  insights: string[];
  rag_chunks: string[] | null;
  approve_argument: string | null;
  reject_argument: string | null;
  mediator_output: Record<string, unknown> | null;
  adjuster_action: string | null;
  error_message?: string | null;
};

function pillClass(d: string | null) {
  const x = (d || "").toUpperCase();
  if (x === "APPROVE") return "pill pill-approve";
  if (x === "REJECT") return "pill pill-reject";
  return "pill pill-review";
}

function riskColor(score: number | null) {
  if (score == null) return "#9a9aaa";
  if (score < 35) return "#4caf50";
  if (score < 65) return "#ffcc00";
  return "#f44336";
}

function gaugeColor(val: number | null) {
  if (val == null) return "#9a9aaa";
  if (val < 25) return "#4caf50";
  if (val < 50) return "#ffcc00";
  if (val < 75) return "#ff9800";
  return "#f44336";
}

export default function Results() {
  const { claimId } = useParams();
  const [data, setData] = useState<Report | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  useEffect(() => {
    if (!claimId) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;

    const tick = async () => {
      try {
        const j = (await getReport(claimId)) as Report;
        if (cancelled) return;
        setData(j);
        if (j.status === "processing" || j.status === "uploaded") {
          timer = setTimeout(tick, 1500);
        }
      } catch (e: unknown) {
        if (!cancelled) setErr(e instanceof Error ? e.message : "Failed to load");
      }
    };
    void tick();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [claimId]);

  async function act(action: "approve" | "reject" | "manual_review") {
    if (!claimId) return;
    setBusy(action);
    try {
      await adjusterAction(claimId, action);
      const j = await getReport(claimId);
      setData(j as Report);
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "Action failed");
    } finally {
      setBusy(null);
    }
  }

  if (err) {
    return (
      <div>
        <div className="flash flash-err">{err}</div>
        <Link to="/claims-mgmt">← Claims mgmt</Link>
      </div>
    );
  }
  if (!data) return <p className="page-sub">Loading report…</p>;

  if (data.status === "processing" || data.status === "uploaded") {
    return (
      <div>
        <p className="muted">Analysis in progress… This page will refresh automatically.</p>
        <p>
          <Link to="/claims-mgmt">← Claims mgmt</Link>
        </p>
      </div>
    );
  }

  if (data.status === "failed") {
    return (
      <div>
        <div className="flash flash-err">{data.error_message || "Analysis failed"}</div>
        <p>
          <Link to="/claims-mgmt">← Claims mgmt</Link>
        </p>
      </div>
    );
  }

  const riskBarData = [
    { name: "Risk score", value: data.risk_score ?? 0, full: 100 },
    { name: "Fraud probability", value: data.fraud_probability ?? 0, full: 100 },
  ];

  const gaugeData = [
    { name: "Fraud probability", value: data.fraud_probability ?? 0 },
    { name: "Remaining", value: 100 - (data.fraud_probability ?? 0) },
  ];
  const gColor = gaugeColor(data.fraud_probability);

  return (
    <div>
      <p>
        <Link to="/claims-mgmt">Claims mgmt</Link>
        {" · "}
        <Link to="/reports">Reports</Link>
      </p>
      <h1 style={{ fontSize: "1.35rem", margin: "0.5rem 0 0.25rem" }}>Result dashboard</h1>
      <p className="muted" style={{ marginBottom: "1rem" }}>
        Claim <code>{data.id}</code>
      </p>

      <div className="card">
        <h2>Decision summary</h2>
        <div style={{ display: "flex", alignItems: "center", gap: "1rem", flexWrap: "wrap", marginBottom: "1rem" }}>
          <span className={pillClass(data.decision)}>{(data.decision || "REVIEW").toUpperCase()}</span>
          {data.adjuster_action ? (
            <span className="muted">Your action: {data.adjuster_action.replace("ADJUSTER_", "")}</span>
          ) : null}
        </div>
        <div className="score-row">
          <div className="score-block">
            <span>Risk score</span>
            <strong>{data.risk_score ?? "—"}</strong>
          </div>
          <div className="score-block">
            <span>Fraud probability</span>
            <strong>{data.fraud_probability != null ? `${data.fraud_probability}%` : "—"}</strong>
          </div>
        </div>
      </div>

      <div className="card">
        <h2>Charts & metrics</h2>
        <div className="charts-grid">
          <div className="chart-box">
            <span className="chart-label">Risk score (0–100)</span>
            <ResponsiveContainer width="100%" height={80}>
              <BarChart data={riskBarData} layout="vertical" margin={{ top: 0, right: 20, bottom: 0, left: 10 }}>
                <XAxis hide type="number" domain={[0, 100]} />
                <YAxis hide type="category" />
                <Tooltip
                  contentStyle={{ background: "#1a1a1a", border: "1px solid #2a2a2a", borderRadius: 8, fontSize: 12 }}
                  formatter={(val) => [`${val}`, ""]}
                />
                <Bar dataKey="value" fill={riskColor(data.risk_score)} radius={[4, 4, 4, 4]} barSize={24} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="chart-box">
            <span className="chart-label">Fraud probability</span>
            <ResponsiveContainer width="100%" height={100}>
              <PieChart>
                <Pie
                  data={gaugeData}
                  cx="50%"
                  cy="50%"
                  startAngle={180}
                  endAngle={0}
                  innerRadius={30}
                  outerRadius={42}
                  dataKey="value"
                  stroke="none"
                >
                  <Cell fill={gColor} />
                  <Cell fill="#2a2a2a" />
                </Pie>
                <Tooltip
                  contentStyle={{ background: "#1a1a1a", border: "1px solid #2a2a2a", borderRadius: 8, fontSize: 12 }}
                  formatter={(val) => [`${val}%`, "Fraud probability"]}
                />
              </PieChart>
            </ResponsiveContainer>
            <div style={{ textAlign: "center", fontSize: "1.1rem", fontWeight: 700, marginTop: "-0.5rem" }}>
              {data.fraud_probability ?? "—"}%
            </div>
          </div>
        </div>
      </div>

      <div className="card">
        <h2>Flags & insights</h2>
        {data.flags?.length ? (
          <ul>
            {data.flags.map((f, i) => (
              <li key={i}>{f}</li>
            ))}
          </ul>
        ) : (
          <p className="muted">No automated flags surfaced.</p>
        )}
        {data.insights?.length ? (
          <div style={{ marginTop: "0.75rem" }}>
            {data.insights.map((t, i) => (
              <p key={i} style={{ margin: "0.35rem 0" }}>
                {t}
              </p>
            ))}
          </div>
        ) : null}
      </div>

      <div className="card">
        <h2>Policy match (RAG excerpts)</h2>
        {data.rag_chunks?.length ? (
          <ul className="muted" style={{ fontSize: "0.9rem" }}>
            {data.rag_chunks.map((c, i) => (
              <li key={i} style={{ marginBottom: "0.5rem" }}>
                {c}
              </li>
            ))}
          </ul>
        ) : (
          <p className="muted">No clauses retrieved.</p>
        )}
      </div>

      <div className="card">
        <h2>AI reasoning</h2>
        <div className="split">
          <div>
            <h3 className="muted" style={{ fontSize: "0.85rem", margin: "0 0 0.5rem" }}>
              Approve argument
            </h3>
            <div className="arg-box arg-approve">{data.approve_argument || "—"}</div>
          </div>
          <div>
            <h3 className="muted" style={{ fontSize: "0.85rem", margin: "0 0 0.5rem" }}>
              Reject / risk argument
            </h3>
            <div className="arg-box arg-reject">{data.reject_argument || "—"}</div>
          </div>
        </div>
      </div>

      <div className="card">
        <h2>Your actions (audit)</h2>
        <p className="muted" style={{ marginTop: 0 }}>
          Record a human disposition. This does not re-run the model — it stores your override for compliance tracking.
        </p>
        <div style={{ display: "flex", gap: "0.6rem", flexWrap: "wrap", marginTop: "0.75rem" }}>
          <button type="button" className="btn-success" disabled={!!busy} onClick={() => act("approve")}>
            Approve claim
          </button>
          <button type="button" className="btn-danger" disabled={!!busy} onClick={() => act("reject")}>
            Reject claim
          </button>
          <button type="button" className="btn-warn" disabled={!!busy} onClick={() => act("manual_review")}>
            Send for manual review
          </button>
        </div>
      </div>

    </div>
  );
}
