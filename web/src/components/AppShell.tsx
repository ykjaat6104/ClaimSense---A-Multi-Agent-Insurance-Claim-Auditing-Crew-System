import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { clearToken } from "../api";

const nav: { to: string; label: string; end?: boolean; icon: string }[] = [
  { to: "/", label: "Dashboard", end: true, icon: "home" },
  { to: "/claims-mgmt", label: "Claims Mgmt.", icon: "doc" },
  { to: "/results", label: "Results", icon: "chart" },
  { to: "/reports", label: "Reports", icon: "report" },
];

function Icon({ name }: { name: string }) {
  const stroke = "currentColor";
  const o = { width: 20, height: 20, fill: "none", strokeWidth: 1.6, strokeLinecap: "round" as const, strokeLinejoin: "round" as const };
  switch (name) {
    case "home":
      return (
        <svg {...o} viewBox="0 0 24 24">
          <path stroke={stroke} d="M4 10.5L12 4l8 6.5V20a1 1 0 0 1-1 1h-5v-6H10v6H5a1 1 0 0 1-1-1v-9.5z" />
        </svg>
      );
    case "doc":
      return (
        <svg {...o} viewBox="0 0 24 24">
          <path stroke={stroke} d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6z" />
          <path stroke={stroke} d="M14 2v6h6M9 15h6M9 11h6" />
        </svg>
      );
    case "bolt":
      return (
        <svg {...o} viewBox="0 0 24 24">
          <path stroke={stroke} d="M13 2L3 14h8l-1 8 10-12h-8l1-8z" />
        </svg>
      );
    case "rupee":
      return (
        <svg {...o} viewBox="0 0 24 24">
          <path stroke={stroke} d="M6 3h12M6 9h12M8 15c2 0 3.5 1 4 3H6M10 9v12" />
        </svg>
      );
    case "user":
      return (
        <svg {...o} viewBox="0 0 24 24">
          <circle stroke={stroke} cx="12" cy="8" r="4" />
          <path stroke={stroke} d="M6 20v-2a4 4 0 0 1 4-4h4a4 4 0 0 1 4 4v2" />
        </svg>
      );
    case "cloud":
      return (
        <svg {...o} viewBox="0 0 24 24">
          <path stroke={stroke} d="M7 18h11a4 4 0 0 0 0-8 1 1 0 0 0-1-1 5 5 0 0 0-9.7 1.7A3.5 3.5 0 0 0 7 18z" />
        </svg>
      );
    case "chart":
      return (
        <svg {...o} viewBox="0 0 24 24">
          <rect stroke={stroke} x="4" y="14" width="4" height="6" rx="1" />
          <rect stroke={stroke} x="10" y="10" width="4" height="10" rx="1" />
          <rect stroke={stroke} x="16" y="6" width="4" height="14" rx="1" />
        </svg>
      );
    case "report":
      return (
        <svg {...o} viewBox="0 0 24 24">
          <path stroke={stroke} d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2M9 5a2 2 0 0 0 2 2h2a2 2 0 0 0 2-2M9 5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2" />
        </svg>
      );
    default:
      return null;
  }
}

function Ticker() {
  const items = [
    { sym: "CLM-VOL", v: "+2.4%", up: true },
    { sym: "FRAUD-IDX", v: "-0.8%", up: false },
    { sym: "SETTLE-T", v: "+1.1%", up: true },
    { sym: "CAT-EXP", v: "-3.2%", up: false },
    { sym: "UW-MGN", v: "+0.6%", up: true },
  ];
  return (
    <div className="ticker">
      {items.map((x) => (
        <span key={x.sym} className="ticker-item">
          <strong>{x.sym}</strong>
          <span className={x.up ? "ticker-up" : "ticker-down"}>{x.v}</span>
        </span>
      ))}
    </div>
  );
}

export default function AppShell() {
  const goto = useNavigate();
  return (
    <div className="app-root">
      <aside className="sidebar">
        <div className="sidebar-brand">ClaimSense</div>
        <nav className="sidebar-nav">
          {nav.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) => "sidebar-link" + (isActive ? " active" : "")}
            >
              <Icon name={item.icon} />
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">
          <button
            type="button"
            className="sidebar-profile-btn"
            onClick={() => goto("/profile")}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="8" r="4" />
              <path d="M6 20v-2a4 4 0 0 1 4-4h4a4 4 0 0 1 4 4v2" />
            </svg>
            Profile
          </button>
          <button
            type="button"
            className="btn-ghost"
            style={{ width: "100%" }}
            onClick={() => {
              clearToken();
              window.location.href = "/login";
            }}
          >
            Sign out
          </button>
        </div>
      </aside>
      <div className="main-wrap">
        <Ticker />
        <main className="main-inner">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
