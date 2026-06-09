import { useEffect, useRef, useState } from "react";
import { getProfile, uploadAvatar, deleteAvatar } from "../api";

export default function Profile() {
  const [username, setUsername] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [avatarUrl, setAvatarUrl] = useState<string | null>(null);
  const [createdAt, setCreatedAt] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    getProfile()
      .then((p) => {
        setUsername(p.username);
        setDisplayName(p.display_name || "");
        setAvatarUrl(p.avatar_url);
        setCreatedAt(p.created_at);
      })
      .catch((e) => setErr(e instanceof Error ? e.message : "Failed to load profile"));
  }, []);

  async function onFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (!f) return;
    if (!["image/jpeg", "image/png"].includes(f.type)) {
      setErr("Only JPEG and PNG images are allowed");
      return;
    }
    if (f.size > 2 * 1024 * 1024) {
      setErr("File size exceeds 2MB limit");
      return;
    }
    setUploading(true);
    setErr(null);
    setOk(null);
    try {
      const res = await uploadAvatar(f);
      setAvatarUrl(res.avatar_url);
      setOk("Avatar updated");
    } catch (ex: unknown) {
      setErr(ex instanceof Error ? ex.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  async function onRemoveAvatar() {
    setErr(null);
    setOk(null);
    try {
      const res = await deleteAvatar();
      setAvatarUrl(res.avatar_url);
      setOk("Avatar removed");
    } catch (ex: unknown) {
      setErr(ex instanceof Error ? ex.message : "Failed to remove avatar");
    }
  }

  function formatDate(iso: string) {
    if (!iso) return "";
    const d = new Date(iso);
    return d.toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" });
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
      {err ? <div className="flash flash-err">{err}</div> : null}
      {ok ? <div className="flash flash-ok">{ok}</div> : null}

      <div className="profile-card">
        <div className="profile-cover">
          <div className="profile-avatar-wrap">
            {avatarUrl ? (
              <img src={avatarUrl} alt="Avatar" className="profile-avatar-img" />
            ) : (
              <div className="profile-avatar-placeholder">{username.charAt(0).toUpperCase()}</div>
            )}
            <button
              type="button"
              className="profile-avatar-edit"
              onClick={() => fileRef.current?.click()}
              disabled={uploading}
              title="Change avatar"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M17 3a2.85 2.85 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z" />
              </svg>
            </button>
            <input
              ref={fileRef}
              type="file"
              accept="image/jpeg,image/png"
              style={{ display: "none" }}
              onChange={onFileChange}
            />
          </div>
          {avatarUrl ? (
            <button type="button" className="profile-avatar-remove" onClick={onRemoveAvatar} title="Remove avatar">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M18 6 6 18" /><path d="m6 6 12 12" />
              </svg>
            </button>
          ) : null}
        </div>

        <div className="profile-body">
          <h2 className="profile-name">{displayName || username}</h2>
          <p className="profile-username">@{username}</p>

          <div className="profile-divider" />

          <div className="profile-meta">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
              <line x1="16" y1="2" x2="16" y2="6" />
              <line x1="8" y1="2" x2="8" y2="6" />
              <line x1="3" y1="10" x2="21" y2="10" />
            </svg>
            <span>Member since {formatDate(createdAt)}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
