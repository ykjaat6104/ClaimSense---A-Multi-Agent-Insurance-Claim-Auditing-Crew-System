import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { downloadDocx, downloadPdf, listClaims } from "../api";

type Row = {
  id: string;
  status: string;
  decision: string | null;
  risk_score: number | null;
  fraud_probability: number | null;
  created_at: string | null;
};

function pillClass(d: string | null) {
  const x = (d || "").toUpperCase();
  if (x === "APPROVE") return "pill pill-approve";
  if (x === "REJECT") return "pill pill-reject";
  return "pill pill-review";
}

export default function ResultsList() {
  const [rows, setRows] = useState<Row[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [busyExport, setBusyExport] = useState<string | null>(null);

  useEffect(() => {
    let on = true;
    (async () => {
      try {
        const data = await listClaims();
        if (on) setRows(data);
      } catch (e: unknown) {
        if (on) setErr(e instanceof Error ? e.message : "Failed to load");
      }
    })();
    return () => { on = false; };
  }, []);

  function exportJson(row: Row) {
    const blob = new Blob([JSON.stringify(row, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `claimsense_${row.id}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  const completed = rows.filter((r) => r.status === "completed");

  return (
    <div>
      <h1 className="page-title">Results</h1>
      <p className="page-sub">
        Completed claim evaluations. Export reports as PDF, JSON, or DOCX.
      </p>
      {err ? <div className="flash flash-err">{err}</div> : null}

      <div className="card">
        <h2>Completed evaluations</h2>
        {completed.length === 0 ? (
          <p className="page-sub" style={{ margin: 0 }}>No completed claims yet. Start from Claims Mgmt.</p>
        ) : (
          <table className="data" style={{ marginTop: "0.5rem" }}>
            <thead>
              <tr>
                <th>Claim ID</th>
                <th>Decision</th>
                <th>Risk</th>
                <th>Fraud %</th>
                <th>Export</th>
              </tr>
            </thead>
            <tbody>
              {completed.map((r) => (
                <tr key={r.id}>
                  <td>
                    <Link to={`/results/${r.id}`}>{r.id.slice(0, 8)}…</Link>
                  </td>
                  <td>
                    <span className={pillClass(r.decision)}>{(r.decision || "REVIEW").toUpperCase()}</span>
                  </td>
                  <td>{r.risk_score ?? "—"}</td>
                  <td>{r.fraud_probability ?? "—"}</td>
                  <td>
                    <div className="export-actions">
                      <button
                        type="button"
                        className="btn-sm"
                        disabled={busyExport === r.id}
                        onClick={async () => {
                          setBusyExport(r.id);
                          await downloadPdf(r.id, `claimsense_${r.id}.pdf`);
                          setBusyExport(null);
                        }}
                      >
                        PDF
                      </button>
                      <button
                        type="button"
                        className="btn-sm-ghost"
                        onClick={() => exportJson(r)}
                      >
                        JSON
                      </button>
                      <button
                        type="button"
                        className="btn-sm-ghost"
                        disabled={busyExport === r.id}
                        onClick={async () => {
                          setBusyExport(r.id);
                          await downloadDocx(r.id, `claimsense_${r.id}.docx`);
                          setBusyExport(null);
                        }}
                      >
                        DOCX
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
