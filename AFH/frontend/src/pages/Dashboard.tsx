import { useFleet } from "../FleetDataContext";
import { ControllerBanner, PendingActions } from "../components";
import { PipelineVisualizer } from "../components/PipelineVisualizer";
import { TimelineView } from "../components/TimelineView";
import { ProvenanceCard } from "../components/ProvenanceCard";
import { HarnessTrustScoreCard } from "../components/HarnessTrustScoreCard";
import { SafetyGuardrailCard } from "../components/SafetyGuardrailCard";
import { LiveExecutionPanel, LiveEventFeed, MissionControlAlert } from "../missioncontrol";

export default function Dashboard() {
  const {
    decision, history, world, actions, audit, technical, approve, reject, runNow, busy,
    sensorDrift, tripCircuitBreaker, runProbe, corruptLlm, killAgent, staleSignal,
  } = useFleet();

  return (
    <div className="page">
      <div className="mc-topline">
        <div className="mc-topline-item">
          <span className="mc-topline-value">{actions.length}</span>
          <span className="mc-topline-label">Pending Decisions</span>
        </div>
        <span className="mc-topline-sep" />
        <div className="mc-topline-item">
          <span className="mc-topline-value">1</span>
          <span className="mc-topline-label">Vehicle Monitored (TRUCK-042)</span>
        </div>
        <span className="mc-topline-sep" />
        <div className="mc-topline-item">
          <span className="mc-topline-value">{history.length}</span>
          <span className="mc-topline-label">Harness Runs Session</span>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "24px", marginBottom: "24px" }}>
        <HarnessTrustScoreCard />
        <SafetyGuardrailCard />
      </div>

      <PipelineVisualizer />

      {/* Failure Injection & Simulation Bar */}
      <div className="failure-injection-bar">
        <span className="injection-label">⚡ LIVE FAILURE INJECTION & SIMULATION:</span>
        <button className="btn-inject" title="Simulate Sensor Drift" onClick={() => sensorDrift(14.5)}>
          🌡️ Sensor Drift (+14.5°C)
        </button>
        <button className="btn-inject" title="Trip LLM Circuit Breaker" onClick={tripCircuitBreaker}>
          ⚡ Trip Circuit Breaker
        </button>
        <button className="btn-inject" title="Inject Malformed LLM Output" onClick={corruptLlm}>
          💥 Corrupt LLM Payload
        </button>
        <button className="btn-inject" title="Kill Truck Sensor Agent A" onClick={() => killAgent("agent_a", true)}>
          🔌 Kill Agent A
        </button>
        <button className="btn-inject" title="Backdate Signal to Stale" onClick={() => staleSignal("cargo_temperature")}>
          ⏱️ Stale Signal
        </button>
        <button className="btn-inject" title="Run Red-Team Security Probe" onClick={runProbe}>
          🛡️ Red-Team Probe
        </button>
      </div>

      <MissionControlAlert actions={actions} />

      <div className="mission-control">
        <LiveExecutionPanel decision={decision} world={world} actions={actions} busy={busy} onRun={runNow} />
        <LiveEventFeed audit={audit} />
      </div>

      <TimelineView />
      <ProvenanceCard />

      {decision && <ControllerBanner d={decision} technical={technical} />}
      <PendingActions actions={actions} onApprove={approve} onReject={reject} technical={technical} />
    </div>
  );
}
