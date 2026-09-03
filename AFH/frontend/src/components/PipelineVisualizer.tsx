import { useFleet } from "../FleetDataContext";

export function PipelineVisualizer() {
  const { decision, world, backend } = useFleet();

  const state = decision?.controller_state ?? "IDLE";
  const confidence = decision ? Math.round(decision.confidence * 100) : 0;
  const criticRejected = decision?.critic_rejected;
  const riskMatrix = decision?.risk_matrix;
  const gateNotes = decision?.trace?.gate_notes ?? [];
  const excludedIds = decision?.trace?.excluded_evidence_ids ?? [];

  // Determine layer statuses
  const agentAActive = !world?.switches.agent_a_disabled;
  const agentBActive = !world?.switches.agent_b_disabled;
  
  const gateStatus = (gateNotes.length > 0 || excludedIds.length > 0)
    ? "warning"
    : "success";

  const criticStatus = criticRejected
    ? "danger"
    : riskMatrix?.risk_level === "HIGH"
    ? "danger"
    : riskMatrix?.risk_level === "MEDIUM"
    ? "warning"
    : "success";

  const controllerStatus = state === "AUTO_OPTIMIZE"
    ? "success"
    : state === "CRITICAL_HALT"
    ? "danger"
    : "warning";

  return (
    <div className="pipeline-visualizer-card">
      <div className="pipeline-header">
        <div className="pipeline-title">
          <span className="live-pulse"></span>
          <h3>5-Layer Decision Pipeline Architecture</h3>
        </div>
        <div className="pipeline-meta">
          <span className="meta-tag">LLM Engine: <strong>{backend}</strong></span>
          <span className="meta-tag">Decision State: <strong className={`state-text-${controllerStatus}`}>{state}</strong></span>
          <span className="meta-tag">Confidence: <strong>{confidence}%</strong></span>
        </div>
      </div>

      <div className="pipeline-flow">
        {/* Layer 1 */}
        <div className="pipeline-step">
          <div className="step-badge">LAYER 1</div>
          <div className="step-card">
            <div className="step-title">Telemetry Agents</div>
            <div className="step-sub">Raw Telematics Stream</div>
            <div className="agent-indicators">
              <span className={`agent-pill ${agentAActive ? "active" : "offline"}`}>
                {agentAActive ? "● Agent A (Truck)" : "✕ Agent A (Killed)"}
              </span>
              <span className={`agent-pill ${agentBActive ? "active" : "offline"}`}>
                {agentBActive ? "● Agent B (Route)" : "✕ Agent B (Killed)"}
              </span>
            </div>
          </div>
        </div>

        <div className="flow-arrow">➔</div>

        {/* Layer 2 */}
        <div className={`pipeline-step step-${gateStatus}`}>
          <div className="step-badge">LAYER 2</div>
          <div className="step-card">
            <div className="step-title">Trust Gate</div>
            <div className="step-sub">Freshness & Provenance</div>
            <div className="step-value">
              {gateStatus === "success" ? "✓ All Signals Fresh" : "⚠️ Filtered / Stale Signals"}
            </div>
          </div>
        </div>

        <div className="flow-arrow">➔</div>

        {/* Layer 3 */}
        <div className={`pipeline-step step-${criticStatus}`}>
          <div className="step-badge">LAYER 3</div>
          <div className="step-card">
            <div className="step-title">Consensus Critic</div>
            <div className="step-sub">LLM OpenRouter Reasoner</div>
            <div className="step-value">
              {criticRejected
                ? "❌ Schema Rejection"
                : `Risk: ${riskMatrix?.risk_level ?? "NONE"}`}
            </div>
          </div>
        </div>

        <div className="flow-arrow">➔</div>

        {/* Layer 4 */}
        <div className={`pipeline-step step-${controllerStatus}`}>
          <div className="step-badge">LAYER 4</div>
          <div className="step-card">
            <div className="step-title">Deterministic Controller</div>
            <div className="step-sub">3-State Machine & Policy</div>
            <div className="step-value">
              {state} ({confidence}%)
            </div>
          </div>
        </div>

        <div className="flow-arrow">➔</div>

        {/* Layer 5 */}
        <div className="pipeline-step">
          <div className="step-badge">LAYER 5</div>
          <div className="step-card">
            <div className="step-title">Action Gateway</div>
            <div className="step-sub">Human-in-the-Loop</div>
            <div className="step-value">
              {state === "CRITICAL_HALT"
                ? "⚠️ Human Approval Needed"
                : "✓ Auto-Executed / Clear"}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
