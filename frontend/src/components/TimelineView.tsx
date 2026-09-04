import { useFleet } from "../FleetDataContext";

export function TimelineView() {
  const { decision } = useFleet();
  const chain = decision?.trace?.decision_chain ?? [];

  if (!decision || chain.length === 0) return null;

  return (
    <div className="timeline-card">
      <div className="timeline-header">
        <div className="timeline-title">
          <span className="live-pulse"></span>
          <h3>Step-by-Step Decision Trace Timeline</h3>
        </div>
        <span className="font-mono text-muted">Run ID: {decision.run_id}</span>
      </div>

      <div className="timeline-steps">
        {chain.map((step, idx) => {
          const statusClass =
            step.status === "OK"
              ? "step-ok"
              : step.status === "WARNING"
              ? "step-warn"
              : "step-failed";

          return (
            <div key={idx} className={`timeline-step-item ${statusClass}`}>
              <div className="step-num">{idx + 1}</div>
              <div className="step-content">
                <div className="step-content-top">
                  <span className="step-name">{step.step_name.toUpperCase()}</span>
                  <span className="step-duration font-mono">{step.duration_ms} ms</span>
                </div>
                <div className="step-detail">{step.detail}</div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
