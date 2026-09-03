import { useLocation } from "react-router-dom";
import { useFleet } from "../FleetDataContext";
import { STATE_META } from "../humanize";
import { BellIcon, SearchIcon } from "../icons";

const TITLES: Record<string, { title: string; sub: string }> = {
  "/": { title: "Dashboard", sub: "Fleet-wide decision-control overview" },
  "/vehicle": { title: "Vehicle Details & Evidence Explorer", sub: "Live telemetry and evidence trust for TRUCK-042" },
  "/pipeline": { title: "Harness Pipeline & Controller", sub: "Sensors → Gate → Critic → Controller → Action" },
  "/simulation": { title: "Simulation Lab", sub: "Drive every scene and failure mode on demand" },
  "/audit": { title: "Audit Logs & Decision Details", sub: "Immutable, append-only record of every run" },
  "/analytics": { title: "Analytics & System Health", sub: "Trends, confidence, and component health" },
  "/settings": { title: "Settings", sub: "View mode, environment, and model configuration" },
};

const USER_EMAIL = "subrato.biswas@trinamix.com";

function initialsOf(email: string): string {
  const name = email.split("@")[0] ?? "";
  const parts = name.split(/[._-]/).filter(Boolean);
  return parts.slice(0, 2).map((p) => p[0]?.toUpperCase() ?? "").join("") || "U";
}

export function Topbar() {
  const { pathname } = useLocation();
  const { decision, technical, setMode } = useFleet();
  const meta = TITLES[pathname] ?? TITLES["/"];
  const state = decision?.controller_state ?? null;
  const tone = state ? STATE_META[state].tone : "idle";

  return (
    <header className="topbar">
      <div>
        <h1 className="topbar-title">{meta.title}</h1>
        <div className="topbar-sub">{meta.sub}</div>
      </div>

      <div className="topbar-search">
        <SearchIcon size={14} />
        <input placeholder="Search vehicles, runs, evidence…" />
      </div>

      <div className="topbar-right">
        <div className="mode-toggle" role="tablist" aria-label="View mode">
          <button role="tab" aria-selected={!technical} className={!technical ? "active" : ""} onClick={() => setMode(false)}>
            Simple
          </button>
          <button role="tab" aria-selected={technical} className={technical ? "active" : ""} onClick={() => setMode(true)}>
            Technical
          </button>
        </div>

        <span className="env-pill">Production</span>

        {state && <span className={`status-pill tone-${tone}`}><span className={`dot dot-${tone}`} />{state}</span>}

        <button className="icon-btn" aria-label="Notifications"><BellIcon size={16} /></button>

        <div className="avatar" title={USER_EMAIL}>{initialsOf(USER_EMAIL)}</div>
      </div>
    </header>
  );
}
