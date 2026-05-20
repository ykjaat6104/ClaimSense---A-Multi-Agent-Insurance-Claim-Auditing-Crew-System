import { useCallback, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getStatus, startProcess, uploadClaimWithProgress } from "../api";

type RowState = {
  key: string;
  label: string;
  file: File | null;
};

function fmtSize(n: number) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

export default function ClaimsMgmt() {
  const nav = useNavigate();
  const [claim, setClaim] = useState<File | null>(null);
  const [invoice, setInvoice] = useState<File | null>(null);
  const [policy, setPolicy] = useState<File | null>(null);
  const [past, setPast] = useState<File | null>(null);
  const [evidence, setEvidence] = useState<File[]>([]);
  const [dragOver, setDragOver] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [claimId, setClaimId] = useState<string | null>(null);
  const [phase, setPhase] = useState<"pick" | "uploaded" | "analyzing">("pick");
  const [upPct, setUpPct] = useState(0);
  const [statusLine, setStatusLine] = useState("");
  const [logs, setLogs] = useState<string[]>([]);
  const fileRef = useRef<HTMLInputElement>(null);

  const rows: RowState[] = [
    { key: "claim", label: "Claim form", file: claim },
    { key: "invoice", label: "Invoice / bill", file: invoice },
    { key: "policy", label: "Policy document", file: policy },
    ...evidence.map((f, i) => ({
      key: `ev-${i}`,
      label: `Evidence ${i + 1}`,
      file: f,
    })),
  ];

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const f = e.dataTransfer.files[0];
      if (!f) return;
      if (!claim) setClaim(f);
      else if (!invoice) setInvoice(f);
      else if (!policy) setPolicy(f);
      else setEvidence((prev) => [...prev, f].slice(0, 5));
    },
    [claim, invoice, policy]
  );

  function buildFormData(): FormData {
    if (!claim || !invoice || !policy) throw new Error("Missing required documents");
    const fd = new FormData();
    fd.append("claim", claim);
    fd.append("invoice", invoice);
    fd.append("policy", policy);
    if (past) fd.append("past_claims", past);
    evidence.slice(0, 5).forEach((f, i) => fd.append(`evidence_${i + 1}`, f));
    return fd;
  }

  async function doUpload() {
    setErr(null);
    if (!claim || !invoice || !policy) {
      setErr("Attach claim form, invoice, and policy.");
      return;
    }
    setBusy(true);
    setUpPct(0);
    try {
      const fd = buildFormData();
      const res = await uploadClaimWithProgress(fd, (p) => setUpPct(p));
      setClaimId(res.claim_id);
      setUpPct(100);
      setPhase("uploaded");
    } catch (ex: unknown) {
      setErr(ex instanceof Error ? ex.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  function friendlyStep(ui: string, lastLog: string) {
    if (ui === "done") return "Analysis complete.";
    if (ui === "error") return "Error during analysis.";
    if (ui === "extract") return "Extracting document data…";
    if (ui === "structure") return "Structuring claim, invoice, and policy data…";
    if (ui === "policy") return "Matching policy clauses…";
    if (ui === "risk") return "Running risk analysis…";
    if (ui === "report") return "Generating report…";
    return lastLog || "Analyzing claim…";
  }

  async function doProcess() {
    if (!claimId) return;
    setErr(null);
    setBusy(true);
    setPhase("analyzing");
    try {
      await startProcess(claimId);
      const pollLoop = async (): Promise<void> => {
        const s = await getStatus(claimId);
        setLogs(s.processing_logs);
        setStatusLine(friendlyStep(s.ui_step, s.processing_logs.at(-1) || ""));
        if (s.status === "completed") {
          nav(`/results/${claimId}`);
          return;
        }
        if (s.status === "failed") {
          setErr(s.error_message || "Analysis failed");
          setPhase("uploaded");
          return;
        }
        await new Promise((r) => setTimeout(r, 1200));
        await pollLoop();
      };
      await pollLoop();
    } catch (ex: unknown) {
      setErr(ex instanceof Error ? ex.message : "Process failed");
      setPhase("uploaded");
    } finally {
      setBusy(false);
    }
  }

  function clearSlot(key: string) {
    if (key === "claim") setClaim(null);
    else if (key === "invoice") setInvoice(null);
    else if (key === "policy") setPolicy(null);
    else if (key.startsWith("ev-")) {
      const i = parseInt(key.split("-")[1], 10);
      setEvidence((prev) => prev.filter((_, j) => j !== i));
    }
  }

  return (
    <div>
      <h1 className="page-title">Claims management</h1>
      <p className="page-sub">
        Upload PDFs, images, or text — policy, claim, invoices, and optional evidence. Drag & drop or browse (max 25 MB per file).
      </p>
      {err ? <div className="flash flash-err">{err}</div> : null}

      {phase === "analyzing" ? (
        <div className="card">
          <h2>Processing</h2>
          <p style={{ fontSize: "1.05rem", marginBottom: "0.75rem" }}>{statusLine}</p>
          <ul style={{ listStyle: "none", padding: 0, margin: 0, color: "var(--muted)", fontSize: "0.88rem" }}>
            {logs.slice(-10).map((l, i) => (
              <li key={i} style={{ padding: "0.25rem 0", borderBottom: "1px solid var(--border)" }}>
                {l}
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <>
          <div className="upload-layout">
            <div
              className={"dropzone-main" + (dragOver ? " drag" : "")}
              onDragOver={(e) => {
                e.preventDefault();
                setDragOver(true);
              }}
              onDragLeave={() => setDragOver(false)}
              onDrop={onDrop}
            >
              <div className="upload-icon">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M12 5v14M5 12l7-7 7 7" />
                </svg>
              </div>
              <div style={{ fontWeight: 600, marginBottom: "0.35rem" }}>Drag files to upload</div>
              <p className="page-sub" style={{ margin: "0 0 1rem" }}>
                Files fill <strong>claim → invoice → policy</strong> first, then attach up to five evidence documents.
              </p>
              <input ref={fileRef} type="file" multiple style={{ display: "none" }} onChange={(e) => {
                const fs = Array.from(e.target.files || []);
                for (const f of fs) {
                  if (!claim) setClaim(f);
                  else if (!invoice) setInvoice(f);
                  else if (!policy) setPolicy(f);
                  else setEvidence((p) => [...p, f].slice(0, 5));
                }
                e.target.value = "";
              }} />
              <button type="button" className="btn-green" onClick={() => fileRef.current?.click()}>
                Choose files
              </button>
            </div>

            <div className="upload-queue">
              <h3>Upload queue</h3>
              {rows.map((r) => (
                <div key={r.key} className="queue-row">
                  <div className="queue-row-top">
                    <div>
                      <div className="queue-name">{r.label}</div>
                      <div className="queue-meta">
                        {r.file ? `${r.file.name} · ${fmtSize(r.file.size)}` : "Not selected"}
                      </div>
                    </div>
                    {r.file ? (
                      <button type="button" className="queue-cancel" aria-label="Remove" onClick={() => clearSlot(r.key)}>
                        ×
                      </button>
                    ) : null}
                  </div>
                  <div className="progress-track">
                    <div
                      className="progress-fill"
                      style={{
                        width:
                          busy
                            ? `${upPct}%`
                            : phase === "uploaded" && r.file
                              ? "100%"
                              : "0%",
                      }}
                    />
                  </div>
                  <div className="queue-meta" style={{ marginTop: "0.25rem" }}>
                    {busy && r.file ? `${upPct}% · uploading…` : r.file ? "Ready" : ""}
                  </div>
                </div>
              ))}

              <div style={{ marginTop: "1rem", display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                {phase === "pick" ? (
                  <button type="button" className="btn-yellow" disabled={busy} onClick={doUpload}>
                    {busy ? "Uploading…" : "Upload to server"}
                  </button>
                ) : (
                  <>
                    <button type="button" className="btn-yellow" disabled={busy} onClick={doProcess}>
                      {busy ? "Working…" : "Process claim"}
                    </button>
                    <button
                      type="button"
                      className="btn-ghost"
                      disabled={busy}
                      onClick={() => {
                        setPhase("pick");
                        setClaimId(null);
                        setClaim(null);
                        setInvoice(null);
                        setPolicy(null);
                        setPast(null);
                        setEvidence([]);
                        setErr(null);
                        setUpPct(0);
                      }}
                    >
                      Reset
                    </button>
                  </>
                )}
              </div>
              {phase === "uploaded" && claimId ? (
                <p className="page-sub" style={{ marginTop: "0.75rem", marginBottom: 0 }}>
                  Stored as <code>{claimId}</code>. Run <strong>Process claim</strong> to start AI analysis.
                </p>
              ) : null}
            </div>
          </div>

          <div className="card" style={{ marginTop: "1rem" }}>
            <h2>Optional: past claims CSV</h2>
            <input type="file" accept=".csv,.txt" onChange={(e) => setPast(e.target.files?.[0] || null)} />
            {past ? <p className="page-sub">{past.name}</p> : null}
          </div>
        </>
      )}
    </div>
  );
}
