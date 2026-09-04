import { useLocation } from "react-router-dom";
import { useFleet } from "../FleetDataContext";
import { STATE_META } from "../humanize";
import { BellIcon } from "../icons";

interface TopbarProps {
  onOpenGuide: () => void;
  onOpenExplainer: () => void;
}

const TITLES: Record<string, { title: string; sub: string }> = {
  "/": { title: "Mission Control Dashboard", sub: "Autonomous fleet safety & decision-control layer" },
  "/vehicle": { title: "TRUCK-042 Cold-Chain Explorer", sub: "Live sensor stream & trust gate validation" },
  "/pipeline": { title: "Decision Pipeline Architecture", sub: "Sensors → Trust Gate → LLM Critic → Controller → Action Gateway" },
  "/runtime": { title: "Harness Runtime", sub: "Supervisor, State Manager, Scheduler, Retry & Policy Engines, Memory, Audit" },
  "/simulation": { title: "Scenario & Failure Mode Lab", sub: "Simulate anomalies, killed agents, and corrupt models" },
  "/audit": { title: "Immutable Audit Log", sub: "Append-only SQLite audit trail & replay store" },
  "/analytics": { title: "Harness Telemetry & Health", sub: "System response time, confidence trends, & module isolation" },
  "/settings": { title: "Harness Configuration", sub: "OpenRouter model keys & threshold settings" },
};

export function Topbar({ onOpenGuide, onOpenExplainer }: TopbarProps) {
  const { pathname } = useLocation();
  const {
    decision, backend, technical, setMode, setScenario, actions,
    emergencyOverride, survivedFailuresCount, timeLapseSpeed, setTimeLapseSpeed,
    autoPlayActive, startAutoPlay,
  } = useFleet();

  const meta = TITLES[pathname] ?? TITLES["/"];
  const state = decision?.controller_state ?? null;
  const tone = state && STATE_META[state] ? STATE_META[state].tone : "idle";

  return (
    <header className="topbar">
      <div className="topbar-left">
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <h1 className="topbar-title">{meta.title}</h1>
          <span className="harness-badge" title="Harness Guarantee">
            🛡️ LLM Zero Decision Authority
          </span>
        </div>
        <div className="topbar-sub">{meta.sub}</div>
      </div>

      <div className="topbar-quick-scenes">
        <span className="scene-label">DEMO SCENES:</span>
        <button className="btn-scene btn-scene-healthy" title="Scene 1: Normal Operation" onClick={() => setScenario("healthy")}>
          🟢 Healthy
        </button>
        <button className="btn-scene btn-scene-risk" title="Scene 2: Contradiction Anomaly" onClick={() => setScenario("compound_risk")}>
          🔴 Risk Anomaly
        </button>
        <button className={`btn-scene ${autoPlayActive ? "active" : ""}`} title="1-Click Auto-Play Presentation" onClick={startAutoPlay}>
          {autoPlayActive ? "⏳ Playing..." : "▶ Auto-Play Demo"}
        </button>
      </div>

      <div className="topbar-right">
        {/* Big Red Button */}
        <button className="btn-emergency-override" title="Big Red Button: Emergency Human Override" onClick={emergencyOverride}>
          🚨 EMERGENCY OVERRIDE
        </button>

        <button className="btn-presenter" onClick={onOpenGuide}>
          ✨ Presenter Script
        </button>

        <button className="btn-explainer" title="Explain Current Decision" onClick={onOpenExplainer}>
          🔍 Why This Decision?
        </button>

        <div className="timelapse-selector" title="Time-Lapse Fast-Forward">
          <span className="timelapse-label font-mono">Speed:</span>
          {[1, 5, 10].map((s) => (
            <button key={s} className={timeLapseSpeed === s ? "active" : ""} onClick={() => setTimeLapseSpeed(s)}>
              {s}x
            </button>
          ))}
        </div>

        <span className="survival-counter font-mono" title="Anomalies Survived Without System Outage">
          🛡️ Survived: {survivedFailuresCount}
        </span>

        <div className="mode-toggle">
          <button className={!technical ? "active" : ""} onClick={() => setMode(false)}>
            Simple
          </button>
          <button className={technical ? "active" : ""} onClick={() => setMode(true)}>
            Technical
          </button>
        </div>

        <span className="model-badge" title="Active Critic Backend">
          🤖 {backend}
        </span>

        {state && (
          <span className={`status-pill tone-${tone}`}>
            <span className={`dot dot-${tone}`} />
            {state}
          </span>
        )}

        {actions.length > 0 && (
          <span className="pending-badge animate-pulse" title="Human Approvals Required">
            <BellIcon size={14} /> {actions.length} Pending
          </span>
        )}
      </div>
    </header>
  );
}
