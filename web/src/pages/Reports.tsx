import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { compareClaims, listClaims } from "../api";

type Row = {
  id: string;
  status: string;
  decision: string | null;
  risk_score: number | null;
  fraud_probability: number | null;
  adjuster_action: string | null;
  created_at: string | null;
};

export default function Reports() {
  const [rows, setRows] = useState<Row[]>([]);
  const [search, setSearch] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [compare, setCompare] = useState<Row[] | null>(null);

  async function load(q?: string) {
    setErr(null);
    try {
      const data = await listClaims(q);
      setRows(data);
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "Failed to load");
    }
  }

  useEffect(() => {
    void load();
  }, []);

  function onSearch(e: FormEvent) {
    e.preventDefault();
    void load(search.trim() || undefined);
  }

  function toggle(id: string) {
    setSelected((prev) => {
      const n = new Set(prev);
      if (n.has(id)) n.delete(id);
      else if (n.size < 6) n.add(id);
      return n;
    });
  }

  async function doCompare() {
    if (selected.size < 2) {
      setErr("Select at least two claims to compare.");
      return;
    }
    setErr(null);
    try {
      const data = await compareClaims([...selected]);
      setCompare(data as Row[]);
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "Compare failed");
    }
  }

  return (
    <div>
      <h1 className="page-title">Reports</h1>
      <p className="page-sub">Search by claim ID, open AI reports, export PDF/JSON from detail pages, and compare risk scores.</p>
      {err ? <div className="flash flash-err">{err}</div> : null}

      <form className="card" onSubmit={onSearch} style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
        <input className="input-dark" placeholder="Claim UUID…" value={search} onChange={(e) => setSearch(e.target.value)} />
        <button type="submit" className="btn-primary">
          Search
        </button>
        <button
          type="button"
          className="btn-ghost"
          onClick={() => {
            setSearch("");
            void load();
          }}
        >
          Reset
        </button>
      </form>

      <div className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "0.75rem" }}>
          <h2 style={{ margin: 0 }}>All submissions</h2>
          <button type="button" className="btn-ghost" onClick={doCompare} disabled={selected.size < 2}>
            Compare selected ({selected.size})
          </button>
        </div>
        <table className="data" style={{ marginTop: "0.75rem" }}>
          <thead>
            <tr>
              <th style={{ width: "36px" }} />
              <th>ID</th>
              <th>Status</th>
              <th>Decision</th>
              <th>Risk</th>
              <th>Fraud %</th>
              <th>Adjuster</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id}>
                <td>
                  <input type="checkbox" checked={selected.has(r.id)} onChange={() => toggle(r.id)} />
                </td>
                <td>
                  <Link to={`/results/${r.id}`}>{r.id.slice(0, 8)}…</Link>
                </td>
                <td>{r.status}</td>
                <td>{r.decision || "—"}</td>
                <td>{r.risk_score ?? "—"}</td>
                <td>{r.fraud_probability ?? "—"}</td>
                <td className="page-sub" style={{ margin: 0 }}>
                  {(r.adjuster_action || "").replace("ADJUSTER_", "") || "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!rows.length ? <p className="page-sub">No claims yet.</p> : null}
      </div>

      {compare?.length ? (
        <div className="card">
          <h2>Risk comparison</h2>
          <table className="data">
            <thead>
              <tr>
                <th>ID</th>
                <th>Risk</th>
                <th>Fraud %</th>
                <th>AI decision</th>
              </tr>
            </thead>
            <tbody>
              {compare.map((r) => (
                <tr key={r.id}>
                  <td>
                    <Link to={`/results/${r.id}`}>{r.id.slice(0, 8)}…</Link>
                  </td>
                  <td>{r.risk_score ?? "—"}</td>
                  <td>{r.fraud_probability ?? "—"}</td>
                  <td>{r.decision || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  );
}
