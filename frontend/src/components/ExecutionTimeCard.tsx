// Per-stage latency, read straight off the same decision_chain durations the
// Live Pipeline already animates — grouped into the five stages a judge cares
// about instead of the raw internal step names.
import { useFleet } from "../FleetDataContext";
import type { DecisionStep } from "../types";

function sumSteps(chain: DecisionStep[], names: string[]): number {
  return chain
    .filter((s) => names.includes(s.step_name))
    .reduce((sum, s) => sum + (s.duration_ms || 0), 0);
}

export function ExecutionTimeCard() {
  const { decision } = useFleet();

  if (!decision) {
    return (
      <div className="panel">
        <h2>Execution Time</h2>
        <div className="empty">Run the harness to see per-stage timing.</div>
      </div>
    );
  }

  const chain = decision.trace.decision_chain ?? [];
  const retries = decision.trace.retries ?? [];
  const all = [...chain, ...retries];

  const stages = [
    { label: "Telemetry", ms: sumSteps(chain, ["agent_vehicle_observer", "agent_environment_observer"]) },
    { label: "Trust Gate", ms: sumSteps(chain, ["trust_gate", "evidence_correlation"]) },
    { label: "Risk Engine", ms: sumSteps(all, ["risk_assessment_engine", "retry_risk_assessment_engine"]) },
    { label: "Verifier", ms: sumSteps(chain, ["verifier_subsystem"]) },
    { label: "Decision", ms: sumSteps(chain, ["deterministic_controller"]) },
  ];
  const total = all.reduce((sum, s) => sum + (s.duration_ms || 0), 0);

  return (
    <div className="panel">
      <h2>Execution Time</h2>
      <div className="exec-time-grid">
        {stages.map((s) => (
          <div className="exec-time-cell" key={s.label}>
            <div className="exec-time-label">{s.label}</div>
            <div className="exec-time-value">{Math.round(s.ms)} ms</div>
          </div>
        ))}
        <div className="exec-time-cell exec-time-total">
          <div className="exec-time-label">Total</div>
          <div className="exec-time-value">{Math.round(total)} ms</div>
        </div>
      </div>
    </div>
  );
}
