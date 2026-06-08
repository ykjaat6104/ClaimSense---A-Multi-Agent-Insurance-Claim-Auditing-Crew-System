import { useCallback, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getStatus, startProcess, uploadClaimWithProgress } from "../api";

function fmtSize(n: number) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

function orderLabel(i: number) {
  const labels = ["1st", "2nd", "3rd", "4th", "5th"];
  return labels[i] || `${i + 1}th`;
}

type SlotKey = "claim" | "invoice" | "policy";
const SLOT_ORDER: SlotKey[] = ["claim", "invoice", "policy"];

function detectSlot(filename: string): SlotKey | null {
  const lower = filename.toLowerCase();
  if (lower.includes("claim")) return "claim";
  if (lower.includes("invoice") || lower.includes("inv_") || lower.includes("inv-") || lower.includes("bill") || lower.includes("receipt")) return "invoice";
  if (lower.includes("policy")) return "policy";
  return null;
}

export default function ClaimsMgmt() {
  const nav = useNavigate();
  const [claim, setClaim] = useState<File | null>(null);
  const [invoice, setInvoice] = useState<File | null>(null);
  const [policy, setPolicy] = useState<File | null>(null);
  const [extra, setExtra] = useState<File[]>([]);
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
  const evRef = useRef<HTMLInputElement>(null);

  function assignFiles(files: FileList | File[], targetEvidence = false) {
    const fs = Array.from(files);
    if (!fs.length) return;

    if (targetEvidence) {
      setEvidence((prev) => [...prev, ...fs].slice(0, 5));
      return;
    }

    let c = claim;
    let i = invoice;
    let p = policy;
    let ex = [...extra];

    for (const f of fs) {
      const detected = detectSlot(f.name);
      let assigned = false;

      if (detected === "claim" && !c) { c = f; assigned = true; }
      else if (detected === "invoice" && !i) { i = f; assigned = true; }
      else if (detected === "policy" && !p) { p = f; assigned = true; }

      if (!assigned) {
        if (!c) c = f;
        else if (!i) i = f;
        else if (!p) p = f;
        else if (ex.length < 5) ex = [...ex, f];
      }
    }

    setClaim(c);
    setInvoice(i);
    setPolicy(p);
    setExtra(ex);
  }

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      assignFiles(e.dataTransfer.files);
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [claim, invoice, policy, extra]
  );

  function onFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    assignFiles(e.target.files || []);
    e.target.value = "";
  }

  function buildFormData(): FormData {
    if (!claim || !invoice || !policy) throw new Error("Missing required documents");
    const fd = new FormData();
    fd.append("claim", claim);
    fd.append("invoice", invoice);
    fd.append("policy", policy);
    extra.slice(0, 5).forEach((f, i) => fd.append(`other_${i + 1}`, f));
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
    } else if (key.startsWith("ex-")) {
      const i = parseInt(key.split("-")[1], 10);
      setExtra((prev) => prev.filter((_, j) => j !== i));
    }
  }

  function firstThree(): { key: SlotKey; label: string; file: File | null; order: number; matched: boolean }[] {
    const filled: SlotKey[] = [];
    for (const k of SLOT_ORDER) {
      const f = k === "claim" ? claim : k === "invoice" ? invoice : policy;
      if (f) filled.push(k);
    }
    return SLOT_ORDER.map((k) => {
      const f = k === "claim" ? claim : k === "invoice" ? invoice : policy;
      return {
        key: k,
        label: k === "claim" ? "Claim form" : k === "invoice" ? "Invoice / bill" : "Policy document",
        file: f,
        order: f ? filled.indexOf(k) + 1 : 0,
        matched: f ? detectSlot(f.name) === k : false,
      };
    });
  }

  const requiredRows = firstThree();
  const requiredFilled = [claim, invoice, policy].filter(Boolean).length;

  return (
    <div>
      <h1 className="page-title">Claims management</h1>
      <p className="page-sub">
        Upload PDFs, images, or text — policy, claim, invoices, and optional evidence. Drag & drop or browse (max 25 MB per file).
        <br />Files are matched to slots by filename (<em>claim</em>, <em>invoice</em>, <em>policy</em>), then fill remaining required slots in order.
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
                Files are smart-matched to <strong>claim</strong>, <strong>invoice</strong>, <strong>policy</strong> slots by filename, then overflow to <strong>extra docs</strong>.
              </p>
              <input
                ref={fileRef}
                type="file"
                multiple
                style={{ display: "none" }}
                onChange={onFileChange}
              />
              <button type="button" className="btn-green" onClick={() => fileRef.current?.click()}>
                Choose files
              </button>
            </div>

            <div className="upload-queue">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
                <h3 style={{ margin: 0 }}>Upload queue</h3>
                <span className="queue-count">
                  {requiredFilled < 3 ? (
                    <span className="req-warn">{requiredFilled}/3 required</span>
                  ) : (
                    <span className="req-ok">3/3 required ✓</span>
                  )}
                </span>
              </div>

              {requiredRows.map((r) => (
                <div key={r.key} className={"queue-row" + (r.file ? " row-filled" : "")}>
                  <div className="queue-row-top">
                    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                      <div>
                        <div className="queue-name">
                          {r.label}
                          <span className="req-dot">*</span>
                        </div>
                        <div className="queue-meta">
                          {r.file ? `${r.file.name} · ${fmtSize(r.file.size)}` : "Not selected"}
                        </div>
                      </div>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
                      {r.file ? <span className="order-badge">{orderLabel(r.order - 1)}</span> : null}
                      {r.file && !r.matched ? (
                        <span className="mismatch-badge" title="Filename didn't match this slot — placed here by order">?</span>
                      ) : null}
                      {r.file ? (
                        <button type="button" className="queue-cancel" aria-label="Remove" onClick={() => clearSlot(r.key)}>
                          ×
                        </button>
                      ) : null}
                    </div>
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

              <div className={"queue-row" + (extra.length ? " row-filled" : "")}>
                <div className="queue-row-top">
                  <div>
                    <div className="queue-name">Extra docs</div>
                    <div className="queue-meta">
                      {extra.length ? `${extra.length} file${extra.length > 1 ? "s" : ""} selected` : "Optional — overflow from main slots"}
                    </div>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.25rem" }}>
                    {extra.length ? <span className="order-badge extra-badge">{extra.length}/5</span> : null}
                    {extra.length ? (
                      <button type="button" className="queue-cancel" aria-label="Clear extra" onClick={() => setExtra([])}>
                        ×
                      </button>
                    ) : null}
                  </div>
                </div>
                {extra.length > 0 ? (
                  <div className="file-list">
                    {extra.map((f, i) => (
                      <span key={i} className="file-tag">
                        {f.name}
                        <button type="button" className="queue-cancel" onClick={() => clearSlot(`ex-${i}`)}>×</button>
                      </span>
                    ))}
                  </div>
                ) : null}
              </div>

              <div className={"queue-row" + (evidence.length ? " row-filled" : "")}>
                <div className="queue-row-top">
                  <div>
                    <div className="queue-name">Evidence</div>
                    <div className="queue-meta">
                      {evidence.length ? `${evidence.length} file${evidence.length > 1 ? "s" : ""} selected` : "Optional — add evidence separately"}
                    </div>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.25rem" }}>
                    {evidence.length ? <span className="order-badge extra-badge">{evidence.length}/5</span> : null}
                  </div>
                </div>
                {evidence.length > 0 ? (
                  <div className="file-list">
                    {evidence.map((f, i) => (
                      <span key={i} className="file-tag">
                        {f.name}
                        <button type="button" className="queue-cancel" onClick={() => clearSlot(`ev-${i}`)}>×</button>
                      </span>
                    ))}
                  </div>
                ) : null}
                <div style={{ marginTop: "0.45rem" }}>
                  <input ref={evRef} type="file" multiple style={{ display: "none" }} onChange={(e) => {
                    assignFiles(e.target.files || [], true);
                    e.target.value = "";
                  }} />
                  <button type="button" className="btn-ghost" style={{ fontSize: "0.78rem", padding: "0.3rem 0.65rem" }} onClick={() => evRef.current?.click()}>
                    + Add evidence files
                  </button>
                </div>
              </div>

              <div style={{ marginTop: "1rem", display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                {phase === "pick" ? (
                  <button type="button" className="btn-yellow" disabled={!requiredFilled || busy} onClick={doUpload}>
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
                        setExtra([]);
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
        </>
      )}
    </div>
  );
}
