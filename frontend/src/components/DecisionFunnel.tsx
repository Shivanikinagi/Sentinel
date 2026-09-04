// One memorable visualization instead of several generic gauges: how many
// runs made it through each gate to reach full automation. Built from the
// same `history` every other Analytics panel uses — real counts, not staged.
import { useFleet } from "../FleetDataContext";

export function DecisionFunnel() {
  const { history } = useFleet();
  const total = history.length;

  const evidenceComplete = history.filter((d) => d.trace.gate_notes.every((n) => !n.startsWith("required"))).length;
  const riskAssessed = history.filter((d) => !d.critic_rejected).length;
  const verifierPassed = history.filter((d) => d.trace.verifier_result?.valid).length;
  const automated = history.filter((d) => d.controller_state === "AUTO_OPTIMIZE").length;

  const stages = [
    { label: "Runs", value: total },
    { label: "Evidence Complete", value: evidenceComplete },
    { label: "Risk Assessed", value: riskAssessed },
    { label: "Verifier Passed", value: verifierPassed },
    { label: "Automation Continued", value: automated },
  ];

  if (total === 0) {
    return (
      <div className="panel">
        <h2>Decision Funnel</h2>
        <div className="empty">Run a few checks to see the funnel.</div>
      </div>
    );
  }

  const max = stages[0].value || 1;

  return (
    <div className="panel">
      <h2>Decision Funnel</h2>
      <div className="funnel">
        {stages.map((s, i) => (
          <div className="funnel-stage" key={s.label}>
            <div className="funnel-bar-track">
              <div className="funnel-bar" style={{ width: `${Math.max(6, (s.value / max) * 100)}%` }}>
                <span className="funnel-count">{s.value}</span>
              </div>
            </div>
            <span className="funnel-label">{s.label}</span>
            {i < stages.length - 1 && <span className="funnel-arrow">↓</span>}
          </div>
        ))}
      </div>
    </div>
  );
}
