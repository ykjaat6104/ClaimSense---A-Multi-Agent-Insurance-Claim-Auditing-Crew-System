import { useEffect, useState } from "react";
import { getProfile } from "../api";

export default function Profile() {
  const [username, setUsername] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [avatarUrl, setAvatarUrl] = useState<string | null>(null);
  const [createdAt, setCreatedAt] = useState("");
  const [err, setErr] = useState<string | null>(null);

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

  function formatDate(iso: string) {
    if (!iso) return "";
    const d = new Date(iso);
    return d.toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" });
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
      {err ? <div className="flash flash-err">{err}</div> : null}

      <div className="profile-card">
        <div className="profile-cover">
          <div className="profile-avatar-wrap">
            {avatarUrl ? (
              <img src={avatarUrl} alt="Avatar" className="profile-avatar-img" />
            ) : (
              <div className="profile-avatar-placeholder">{username.charAt(0).toUpperCase()}</div>
            )}
          </div>
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
