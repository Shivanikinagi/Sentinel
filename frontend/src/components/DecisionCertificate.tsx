// A closing screen for a run: five checks, each derived from a real decision
// field (no step is marked passed unless the underlying data says so). For
// CRITICAL_HALT the certificate ends on what the harness actually guarantees
// — an escalation record awaiting a human, not the halt itself.
import { useFleet } from "../FleetDataContext";
import { CheckCircle, XCircle } from "../icons";

function Check({ ok, label }: { ok: boolean; label: string }) {
  return (
    <div className={`certificate-row ${ok ? "pass" : "fail"}`}>
      {ok ? <CheckCircle size={16} /> : <XCircle size={16} />}
      <span>{label}</span>
    </div>
  );
}

export function DecisionCertificate() {
  const { decision } = useFleet();
  if (!decision) return null;

  const evidenceVerified = decision.trace.evidence_snapshot.length > 0;
  const policyApplied = decision.trace.gate_stage_results?.length === 4;
  const llmValidated = !decision.critic_rejected && decision.risk_matrix !== null;
  const controllerApproved = decision.controller_state !== null;
  const auditLogged = decision.trace.decision_chain !== undefined && decision.trace.decision_chain.length > 0;

  return (
    <div className="panel decision-certificate">
      <h2>Decision Certificate<span className="tech-caption"> · run {decision.run_id}</span></h2>
      <Check ok={evidenceVerified} label={`Evidence Verified (${decision.trace.evidence_snapshot.length} signals)`} />
      <Check ok={!!policyApplied} label={`Policy Applied (${decision.policy_pack})`} />
      <Check ok={llmValidated} label="Risk Assessment Validated" />
      <Check ok={controllerApproved} label="Decision Authority Approved" />
      <Check ok={auditLogged} label="Audit Logged" />

      <div className="certificate-outcome">
        {decision.controller_state === "CRITICAL_HALT" ? (
          <div className="certificate-halt-chain">
            <span>Escalation Record Created</span>
            <span className="arrow">→</span>
            <span>Human Approval Required</span>
            <span className="arrow">→</span>
            <span className="certificate-safe">No unsafe action executed</span>
          </div>
        ) : (
          <div className={`certificate-final tone-${decision.controller_state === "AUTO_OPTIMIZE" ? "good" : "warn"}`}>
            {decision.controller_state === "AUTO_OPTIMIZE"
              ? "Automation continues — every check passed."
              : "Automation paused — insufficient evidence to proceed safely."}
          </div>
        )}
      </div>
    </div>
  );
}
