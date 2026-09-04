import { NavLink } from "react-router-dom";
import { useFleet } from "../FleetDataContext";
import { STATE_META } from "../humanize";
import {
  ActivityIcon, BarChartIcon, ClipboardIcon, FlaskIcon, GridIcon,
  SearchCarIcon, SettingsIcon, ShieldIcon, ZapIcon,
} from "../icons";

const NAV = [
  { to: "/", label: "Dashboard", icon: GridIcon, end: true },
  { to: "/runtime", label: "Harness Runtime", icon: ZapIcon },
  { to: "/vehicle", label: "Vehicle Explorer", icon: SearchCarIcon },
  { to: "/pipeline", label: "Harness Pipeline", icon: ActivityIcon },
  { to: "/simulation", label: "Simulation Lab", icon: FlaskIcon },
  { to: "/audit", label: "Audit Logs", icon: ClipboardIcon },
  { to: "/analytics", label: "Analytics", icon: BarChartIcon },
];

export function Sidebar() {
  const { decision, backend } = useFleet();
  const state = decision?.controller_state ?? null;
  const tone = state ? STATE_META[state].tone : "idle";

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="brand-mark"><ShieldIcon size={18} /></div>
        <div>
          <div className="brand-name">Fleet-Harness</div>
          <div className="brand-tag">AI Decision-Control Layer</div>
        </div>
      </div>

      <nav className="sidebar-nav">
        {NAV.map(({ to, label, icon: Icon, end }) => (
          <NavLink key={to} to={to} end={end} className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}>
            <Icon size={16} />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-spacer" />

      <NavLink to="/settings" className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}>
        <SettingsIcon size={16} />
        <span>Settings</span>
      </NavLink>

      <div className={`sidebar-status tone-${tone}`}>
        <div className="sidebar-status-top">
          <span className={`dot dot-${tone}`} />
          <span className="sidebar-status-label">Controller Status</span>
        </div>
        <div className="sidebar-status-value">{state ?? "STANDBY"}</div>
        <div className="sidebar-status-sub">
          {state === "AUTO_OPTIMIZE" ? "Autonomously operating"
            : state === "CRITICAL_HALT" ? "Halted — awaiting approval"
            : state === "INSUFFICIENT_DATA" ? "Degraded confidence"
            : `Model: ${backend}`}
        </div>
      </div>
    </aside>
  );
}
