const TOKEN_KEY = "claimsense_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(t: string) {
  localStorage.setItem(TOKEN_KEY, t);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

function headers(): HeadersInit {
  const t = getToken();
  const h: Record<string, string> = { Accept: "application/json" };
  if (t) h.Authorization = `Bearer ${t}`;
  return h;
}

export async function apiSignup(username: string, password: string) {
  const r = await fetch("/api/auth/signup", {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!r.ok) throw new Error((await r.json().catch(() => ({})))?.detail || `Signup failed (${r.status})`);
  return r.json() as Promise<{ access_token: string; username: string }>;
}

export async function apiLogin(username: string, password: string) {
  const r = await fetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!r.ok) throw new Error((await r.json().catch(() => ({})))?.detail || `Login failed (${r.status})`);
  return r.json() as Promise<{ access_token: string; username: string }>;
}

export async function apiFetch(path: string, init: RequestInit = {}) {
  const base = headers() as Record<string, string>;
  const extra = (init.headers as Record<string, string> | undefined) || {};
  const r = await fetch(path, {
    ...init,
    headers: { ...base, ...extra },
  });
  if (r.status === 401) {
    clearToken();
    window.location.href = "/login";
    throw new Error("Session expired");
  }
  if (!r.ok) {
    let msg = `${r.status}`;
    try {
      const j = await r.json();
      msg = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail || j);
    } catch {
      /* noop */
    }
    throw new Error(msg);
  }
  return r;
}

export function uploadClaimWithProgress(
  fd: FormData,
  onProgress: (pct: number) => void
): Promise<{ claim_id: string; status: string }> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/api/upload-claim");
    const t = getToken();
    if (t) xhr.setRequestHeader("Authorization", `Bearer ${t}`);
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) onProgress(Math.round((100 * e.loaded) / e.total));
    };
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText));
        } catch {
          reject(new Error("Invalid server response"));
        }
      } else {
        try {
          const j = JSON.parse(xhr.responseText);
          reject(new Error(typeof j.detail === "string" ? j.detail : "Upload failed"));
        } catch {
          reject(new Error(`Upload failed (${xhr.status})`));
        }
      }
    };
    xhr.onerror = () => reject(new Error("Network error"));
    xhr.send(fd);
  });
}

export async function downloadDocx(claimId: string, filename: string) {
  const r = await apiFetch(`/api/claims/${claimId}/docx`);
  const blob = await r.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export async function uploadClaim(files: {
  claim: File;
  invoice: File;
  policy: File;
  pastClaims?: File | null;
  evidence?: File[];
  otherDocs?: File[];
}) {
  const fd = new FormData();
  fd.append("claim", files.claim);
  fd.append("invoice", files.invoice);
  fd.append("policy", files.policy);
  if (files.pastClaims) fd.append("past_claims", files.pastClaims);
  (files.evidence || []).slice(0, 5).forEach((f, i) => {
    fd.append(`evidence_${i + 1}`, f);
  });
  (files.otherDocs || []).slice(0, 5).forEach((f, i) => {
    fd.append(`other_${i + 1}`, f);
  });
  const r = await fetch("/api/upload-claim", { method: "POST", headers: headers(), body: fd });
  if (!r.ok) {
    let msg = "Upload failed";
    try {
      const j = await r.json();
      msg = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail || j);
    } catch {
      /* noop */
    }
    throw new Error(msg);
  }
  return r.json() as Promise<{ claim_id: string; status: string }>;
}

export async function startProcess(claimId: string) {
  const r = await apiFetch(`/api/claims/${claimId}/process`, { method: "POST" });
  return r.json() as Promise<{ claim_id: string; status: string; message: string }>;
}

export async function getStatus(claimId: string) {
  const r = await apiFetch(`/api/claims/${claimId}/status`);
  return r.json() as Promise<{
    id: string;
    status: string;
    processing_logs: string[];
    ui_step: string;
    error_message: string | null;
  }>;
}

export async function getReport(claimId: string) {
  const r = await apiFetch(`/api/claims/${claimId}`);
  return r.json();
}

export async function listClaims(search?: string) {
  const q = search ? `?search=${encodeURIComponent(search)}` : "";
  const r = await apiFetch(`/api/claims${q}`);
  return r.json() as Promise<
    {
      id: string;
      status: string;
      decision: string | null;
      risk_score: number | null;
      fraud_probability: number | null;
      adjuster_action: string | null;
      created_at: string | null;
    }[]
  >;
}

export async function compareClaims(ids: string[]) {
  const r = await apiFetch(`/api/claims/compare?ids=${encodeURIComponent(ids.join(","))}`);
  return r.json() as Promise<
    {
      id: string;
      risk_score: number | null;
      fraud_probability: number | null;
      decision: string | null;
    }[]
  >;
}

export async function adjusterAction(claimId: string, action: "approve" | "reject" | "manual_review") {
  const r = await apiFetch(`/api/claims/${claimId}/adjuster-action`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action }),
  });
  return r.json();
}

export async function downloadPdf(claimId: string, filename: string) {
  const r = await apiFetch(`/api/claims/${claimId}/pdf`);
  const blob = await r.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
