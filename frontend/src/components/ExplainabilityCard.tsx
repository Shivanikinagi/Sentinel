// "Why did the harness decide this?" in plain checklist form — every line
// reads off the same ControllerDecision every other panel uses (RiskMatrix,
// ConfidenceBreakdown, DecisionTrace). Nothing here is a canned script: an
// unhealthy run shows the checks that actually failed, not a happy list.
import { useFleet } from "../FleetDataContext";
import { prettify, riskScore, signalLabel, STATE_META } from "../humanize";
import { CheckCircle, XCircle } from "../icons";

export function ExplainabilityCard() {
  const { decision } = useFleet();

  if (!decision) {
    return (
      <div className="panel">
        <h2>AI Explainability</h2>
        <div className="empty">Run the harness to see why the decision was made.</div>
      </div>
    );
  }

  const approved = decision.controller_state === "AUTO_OPTIMIZE";
  const t = decision.trace;
  const signals = decision.confidence_breakdown?.signals ?? [];
  const trustedCount = t.evidence_snapshot.length - t.excluded_evidence_ids.length;
  const totalCount = t.evidence_snapshot.length;
  const freshPct = totalCount ? Math.round((trustedCount / totalCount) * 100) : 0;
  const score = riskScore(decision.risk_matrix, decision.critic_rejected);
  const confidencePct = Math.round((decision.composite_confidence?.composite ?? decision.confidence) * 100);

  const checks: { ok: boolean; label: string }[] = [
    ...signals.map((s) => ({ ok: s.trusted, label: `${signalLabel(s.signal)} ${s.trusted ? "trusted" : "untrusted"}` })),
    { ok: t.agents_unavailable.length === 0, label: t.agents_unavailable.length === 0 ? "All sensors reporting" : `${t.agents_unavailable.length} sensor group(s) unavailable` },
    { ok: t.excluded_evidence_ids.length === 0, label: t.excluded_evidence_ids.length === 0 ? "Evidence fresh" : `${t.excluded_evidence_ids.length} reading(s) excluded as stale/untrusted` },
    { ok: !decision.risk_matrix?.contradiction_detected, label: decision.risk_matrix?.contradiction_detected ? "Contradiction detected" : "No contradiction detected" },
    { ok: !decision.critic_rejected, label: decision.critic_rejected ? "AI output failed schema validation" : "AI output passed validation" },
  ];

  const riskExplain: { ok: boolean; label: string }[] = [
    { ok: !decision.risk_matrix?.contradiction_detected, label: "No contradiction detected" },
    { ok: (decision.risk_matrix?.missing_evidence.length ?? 0) === 0, label: (decision.risk_matrix?.missing_evidence.length ?? 0) === 0 ? "No missing evidence" : `Missing: ${decision.risk_matrix!.missing_evidence.map(signalLabel).join(", ")}` },
    { ok: t.excluded_evidence_ids.length === 0, label: t.excluded_evidence_ids.length === 0 ? "No stale evidence" : `${t.excluded_evidence_ids.length} stale reading(s) excluded` },
    { ok: t.agents_unavailable.length === 0, label: t.agents_unavailable.length === 0 ? "All sensors trusted" : "Some sensors unavailable" },
  ];

  return (
    <div className="panel">
      <h2>AI Explainability</h2>

      <div className="explain-summary">
        <div className="explain-summary-field">
          <div className="explain-summary-label">Decision</div>
          <div className={`explain-summary-value tone-${STATE_META[decision.controller_state].tone}`}>{decision.controller_state}</div>
        </div>
        <div className="explain-summary-field">
          <div className="explain-summary-label">Confidence</div>
          <div className="explain-summary-value">{confidencePct}%</div>
        </div>
        <div className="explain-summary-field">
          <div className="explain-summary-label">Risk Score</div>
          <div className={`explain-summary-value tone-${score >= 70 ? "bad" : score >= 40 ? "warn" : "good"}`}>{score} / 100</div>
        </div>
        <div className="explain-summary-field">
          <div className="explain-summary-label">Trust Gate</div>
          <div className="explain-summary-value" style={{ fontSize: 13 }}>
            {trustedCount} Trusted · {t.excluded_evidence_ids.length} Excluded · {freshPct}% Fresh
          </div>
        </div>
        <div className="explain-summary-field">
          <div className="explain-summary-label" title="This vehicle's recent non-halt rate — 100% with no history yet">Historical Reliability</div>
          <div className="explain-summary-value">
            {decision.composite_confidence ? `${Math.round(decision.composite_confidence.historical_reliability * 100)}%` : "—"}
          </div>
          {decision.composite_confidence && decision.composite_confidence.historical_reliability < 1 && (
            <div className="explain-summary-sub">past halts lowered today's confidence</div>
          )}
        </div>
      </div>
      <div className="explain-reason">{prettify(decision.controller_state)} — {decision.risk_matrix?.reasoning_summary ?? "All trusted evidence passed policy validation."}</div>

      <div className="explain-columns">
        <div>
          <div className="explain-heading">{approved ? "Why was this approved?" : "Why wasn't this approved?"}</div>
          <ul className="explain-list">
            {checks.map((c) => (
              <li key={c.label} className={c.ok ? "ok" : "bad"}>
                {c.ok ? <CheckCircle size={14} /> : <XCircle size={14} />} {c.label}
              </li>
            ))}
          </ul>
        </div>
        <div>
          <div className="explain-heading">Why not HIGH risk?</div>
          {decision.risk_matrix?.risk_level === "HIGH" ? (
            <div className="explain-list-empty">Risk level is HIGH this run — see risk factors above.</div>
          ) : (
            <ul className="explain-list">
              {riskExplain.map((c) => (
                <li key={c.label} className={c.ok ? "ok" : "bad"}>
                  {c.ok ? <CheckCircle size={14} /> : <XCircle size={14} />} {c.label}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
