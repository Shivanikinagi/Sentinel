import { useLocation } from "react-router-dom";
import { useFleet } from "../FleetDataContext";

const TITLES: Record<string, { title: string; sub: string }> = {
  "/": { title: "Mission Control Dashboard", sub: "" },
  "/vehicle": { title: "TRUCK-042 Cold-Chain Explorer", sub: "Live sensor stream & trust gate validation" },
  "/pipeline": { title: "Decision Pipeline Architecture", sub: "Sensors → Trust Gate → LLM Critic → Controller → Action Gateway" },
  "/runtime": { title: "Harness Runtime", sub: "Live proof of how this run's decision was reached" },
  "/isolation": { title: "Agent Isolation", sub: "No callable path between the Vehicle and Environment agents" },
  "/simulation": { title: "Scenario & Failure Mode Lab", sub: "Simulate anomalies, killed agents, and corrupt models" },
  "/audit": { title: "Immutable Audit Log", sub: "Append-only SQLite audit trail & replay store" },
  "/analytics": { title: "Harness Telemetry & Health", sub: "System response time, confidence trends, & module isolation" },
  "/settings": { title: "Harness Configuration", sub: "OpenRouter model keys & threshold settings" },
};

export function Topbar() {
  const { pathname } = useLocation();
  const { emergencyOverride } = useFleet();

  const meta = TITLES[pathname] ?? TITLES["/"];

  return (
    <header className="topbar">
      <div className="topbar-left">
        <h1 className="topbar-title">{meta.title}</h1>
        {meta.sub && <div className="topbar-sub">{meta.sub}</div>}
      </div>

      <div className="topbar-right">
        {/* Big Red Button — deliberately isolated, not grouped */}
        <button className="btn-emergency-override" title="Big Red Button: Emergency Human Override" onClick={emergencyOverride}>
          🚨 OVERRIDE
        </button>
      </div>
    </header>
  );
}
