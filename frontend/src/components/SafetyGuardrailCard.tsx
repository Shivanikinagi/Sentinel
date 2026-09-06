// "Why Harness?" in one screen — two arrow chains, nothing more. The one
// screen a judge should remember even if they saw nothing else.
import { useFleet } from "../FleetDataContext";

export function SafetyGuardrailCard() {
  const { decision } = useFleet();
  const hasRisk = decision?.controller_state === "CRITICAL_HALT" || decision?.risk_matrix?.risk_level === "HIGH";

  return (
    <div className="guardrail-card">
      <div className="guardrail-header">
        <h3>Why a Harness?</h3>
      </div>
      <div className="guardrail-comparison">
        <div className="comparison-box without-harness">
          <div className="box-title"><span>❌ WITHOUT HARNESS</span></div>
          <div className="box-chain">Data → AI → Action <span className="box-warn">⚠️</span></div>
          <div className="box-tag tag-danger">{hasRisk ? "Unverified risk → acted on anyway" : "No check, no audit, no human"}</div>
        </div>
        <div className="comparison-box with-harness">
          <div className="box-title"><span>🛡️ WITH FLEET-HARNESS</span></div>
          <div className="box-chain">Agents → Trust → Reasoning → Verification → Policy → Authority → Human → Action</div>
          <div className="box-tag tag-success">{hasRisk ? "Risk caught → halted for approval" : "Every step checked, every halt approved"}</div>
        </div>
      </div>
    </div>
  );
}
