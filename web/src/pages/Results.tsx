import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { adjusterAction, downloadPdf, getReport } from "../api";

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

  function exportJson() {
    if (!data) return;
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `claimsense_${data.id}.json`;
    a.click();
    URL.revokeObjectURL(url);
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

      <div className="card">
        <h2>Exports</h2>
        <div style={{ display: "flex", gap: "0.6rem", flexWrap: "wrap" }}>
          <button type="button" className="btn-primary" onClick={() => claimId && downloadPdf(claimId, `claimsense_${claimId}.pdf`)}>
            Download PDF
          </button>
          <button type="button" className="btn-ghost" onClick={exportJson}>
            Export JSON
          </button>
        </div>
      </div>
    </div>
  );
}
