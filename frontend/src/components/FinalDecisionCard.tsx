// The single largest visual on the page — the answer to "what was the final
// decision?" must be unmissable, since that's the one thing a judge should
// remember after 60 seconds. Replaces the old ControllerBanner.
import { useFleet } from "../FleetDataContext";
import { humanizeReason } from "../humanize";
import { AlertTriangle, CheckCircle, XCircle } from "../icons";
import type { ControllerState } from "../types";

const DECISION_META: Record<ControllerState, {
  emoji: string; tone: string; automation: string; icon: typeof CheckCircle; explanation: string;
}> = {
  AUTO_OPTIMIZE: {
    emoji: "🟢", tone: "good", automation: "Automation Continues", icon: CheckCircle,
    explanation: "No verified risk detected after Trust Gate, Verifier, and Decision Authority completed.",
  },
  INSUFFICIENT_DATA: {
    emoji: "🟡", tone: "warn", automation: "Automation Paused — No Action Taken", icon: AlertTriangle,
    explanation: "The harness does not hallucinate or guess when evidence is incomplete or unverifiable — it fails safely to INSUFFICIENT_DATA instead.",
  },
  CRITICAL_HALT: {
    emoji: "🔴", tone: "bad", automation: "Automation Halted", icon: XCircle,
    explanation: "Verified risk was confirmed by the Trust Gate, Verifier, and Decision Authority — automation halts pending human approval.",
  },
};

export function FinalDecisionCard() {
  const { decision } = useFleet();
  if (!decision) return null;

  const meta = DECISION_META[decision.controller_state];
  const Icon = meta.icon;
  const verifierValid = decision.trace.verifier_result?.valid ?? false;

  return (
    <div className={`final-decision-card tone-${meta.tone}`}>
      <div className="fd-top">
        <div className="fd-icon"><Icon size={40} /></div>
        <div>
          <div className="fd-headline">{meta.emoji} {decision.controller_state}</div>
          <div className="fd-automation">{meta.automation}</div>
        </div>
      </div>

      <div className="fd-tags">
        <span className="fd-tag">Controller Decision</span>
        <span className={`fd-tag ${verifierValid ? "fd-tag-good" : "fd-tag-bad"}`}>
          {verifierValid ? "Evidence Verified" : "Evidence Unverified"}
        </span>
        <span className="fd-tag">Confidence: {Math.round(decision.confidence * 100)}%</span>
        <span className="fd-tag">Vehicle: {decision.vehicle_id}</span>
      </div>

      <div className="fd-explanation">{meta.explanation}</div>
      <div className="fd-reason">{humanizeReason(decision.reason)}</div>
    </div>
  );
}
