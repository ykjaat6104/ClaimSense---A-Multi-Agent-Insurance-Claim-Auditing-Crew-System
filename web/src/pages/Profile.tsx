import { FormEvent, useEffect, useRef, useState } from "react";
import { getProfile, updateProfile, uploadAvatar, deleteAvatar } from "../api";

export default function Profile() {
  const [username, setUsername] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [avatarUrl, setAvatarUrl] = useState<string | null>(null);
  const [createdAt, setCreatedAt] = useState("");
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);
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

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setErr(null);
    setOk(null);
    if (!displayName.trim()) {
      setErr("Display name is required");
      return;
    }
    setSaving(true);
    try {
      const p = await updateProfile(displayName.trim());
      setDisplayName(p.display_name || "");
      setOk("Profile updated");
    } catch (ex: unknown) {
      setErr(ex instanceof Error ? ex.message : "Update failed");
    } finally {
      setSaving(false);
    }
  }

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
    <div>
      <h1 className="page-title">Profile</h1>
      <p className="page-sub">Manage your account details and avatar.</p>
      {err ? <div className="flash flash-err">{err}</div> : null}
      {ok ? <div className="flash flash-ok">{ok}</div> : null}

      <div className="profile-card">
        <div className="profile-avatar-section">
          <div className="profile-avatar">
            {avatarUrl ? (
              <img src={avatarUrl} alt="Avatar" className="profile-avatar-img" />
            ) : (
              <div className="profile-avatar-placeholder">{username.charAt(0).toUpperCase()}</div>
            )}
          </div>
          <div className="profile-avatar-actions">
            <button type="button" className="btn-ghost" onClick={() => fileRef.current?.click()} disabled={uploading}>
              {uploading ? "Uploading…" : "Upload photo"}
            </button>
            {avatarUrl ? (
              <button type="button" className="btn-ghost" onClick={onRemoveAvatar} style={{ color: "var(--red)" }}>
                Remove
              </button>
            ) : null}
            <input
              ref={fileRef}
              type="file"
              accept="image/jpeg,image/png"
              style={{ display: "none" }}
              onChange={onFileChange}
            />
            <span className="page-sub" style={{ fontSize: "0.75rem", marginTop: "0.25rem" }}>
              JPEG or PNG, max 2MB
            </span>
          </div>
        </div>

        <div className="profile-details">
          <form onSubmit={onSubmit}>
            <label>
              <span>Username</span>
              <input value={username} disabled className="profile-readonly" />
            </label>
            <label>
              <span>Display Name</span>
              <input value={displayName} onChange={(e) => setDisplayName(e.target.value)} />
            </label>
            <label>
              <span>Member since</span>
              <input value={formatDate(createdAt)} disabled className="profile-readonly" />
            </label>
            <button type="submit" className="btn-primary" disabled={saving} style={{ marginTop: "0.5rem" }}>
              {saving ? "Saving…" : "Save changes"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
