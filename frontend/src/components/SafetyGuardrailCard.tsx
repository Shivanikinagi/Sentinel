import { useFleet } from "../FleetDataContext";

export function SafetyGuardrailCard() {
  const { decision } = useFleet();

  const state = decision?.controller_state ?? "IDLE";
  const hasRisk = state === "CRITICAL_HALT" || decision?.risk_matrix?.risk_level === "HIGH";

  return (
    <div className="guardrail-card">
      <div className="guardrail-header">
        <h3>⚡ What Could Have Gone Wrong? (Safety Guardrail Proof)</h3>
        <span className="badge badge-purple">Harness Boundary Defense</span>
      </div>

      <div className="guardrail-comparison">
        {/* Without Harness */}
        <div className="comparison-box without-harness">
          <div className="box-title">
            <span>❌ WITHOUT HARNESS</span>
            <span className="text-muted">(Direct LLM Control)</span>
          </div>
          <p className="box-desc">
            {hasRisk
              ? "Unconstrained LLM interprets contradictory cooling telemetry, hallucinates safe state, and auto-disables cargo refrigeration -> $85,000 cargo spoilage & thermal runaway."
              : "LLM has raw database access and direct authority to invoke fleet APIs without audit trail or validation checks."}
          </p>
          <div className="box-tag tag-danger">OUTCOME: Critical Failure / Spoilage</div>
        </div>

        {/* With Harness */}
        <div className="comparison-box with-harness">
          <div className="box-title">
            <span>🛡️ WITH FLEET-HARNESS</span>
            <span className="text-muted">(Deterministic Layer 2 Boundary)</span>
          </div>
          <p className="box-desc">
            {hasRisk
              ? "Harness Trust Gate & Correlation Engine detect physical contradiction. Deterministic Controller forces CRITICAL_HALT and queues Human-in-the-Loop Action Approval -> Cargo Saved."
              : "Strict Pydantic RiskMatrix validation (extra='forbid'), Verifier check, and 3-state deterministic controller maintain 100% safety."}
          </p>
          <div className="box-tag tag-success">OUTCOME: Fleet Safe & Audited</div>
        </div>
      </div>
    </div>
  );
}
