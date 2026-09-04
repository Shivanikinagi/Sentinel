import { useEffect, useState } from "react";
import { useFleet } from "../FleetDataContext";
import { stepLabel } from "../humanize";
import type { DecisionStep } from "../types";

function statusClassOf(step: DecisionStep): string {
  return step.status === "OK" ? "step-ok" : step.status === "WARNING" ? "step-warn" : "step-failed";
}

export function TimelineView() {
  const { decision } = useFleet();
  const chain = decision?.trace?.decision_chain ?? [];
  const gateStages = decision?.trace?.gate_stage_results ?? [];

  const [replaying, setReplaying] = useState(false);
  const [visibleCount, setVisibleCount] = useState(chain.length);

  useEffect(() => {
    setVisibleCount(chain.length);
    setReplaying(false);
  }, [decision?.run_id]);

  const replay = () => {
    if (replaying || chain.length === 0) return;
    setReplaying(true);
    setVisibleCount(0);
    let i = 0;
    const tick = () => {
      i += 1;
      setVisibleCount(i);
      if (i < chain.length) {
        const delay = Math.min(600, Math.max(180, chain[i]?.duration_ms ?? 0));
        setTimeout(tick, delay);
      } else {
        setReplaying(false);
      }
    };
    setTimeout(tick, 180);
  };

  if (!decision || chain.length === 0) return null;

  return (
    <div className="timeline-card">
      <div className="timeline-header">
        <div className="timeline-title">
          <span className="live-pulse"></span>
          <h3>Step-by-Step Decision Trace Timeline</h3>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <span className="font-mono text-muted">Run ID: {decision.run_id}</span>
          <button className="link-btn" disabled={replaying} onClick={replay}>
            {replaying ? "Replaying…" : "▶ Replay Incident"}
          </button>
        </div>
      </div>

      <div className="timeline-steps">
        {chain.slice(0, visibleCount).map((step, idx) => {
          const isRetry = step.step_name.startsWith("retry_");
          return (
            <div key={idx} className={`timeline-step-item ${statusClassOf(step)}${isRetry ? " step-retry" : ""}`}>
              <div className="step-num">{isRetry ? "↻" : idx + 1}</div>
              <div className="step-content">
                <div className="step-content-top">
                  <span className="step-name">
                    {isRetry && <span className="badge badge-warning" style={{ marginRight: 6 }}>RETRY</span>}
                    {stepLabel(step.step_name)}
                  </span>
                  <span className="step-duration font-mono">{step.duration_ms} ms</span>
                </div>
                <div className="step-detail">{step.detail}</div>

                {step.step_name === "trust_gate" && gateStages.length > 0 && (
                  <div className="gate-stage-breakdown">
                    {gateStages.map((gs) => (
                      <div key={gs.step_name} className={`gate-stage-chip ${statusClassOf(gs)}`}>
                        <span className="gate-stage-name">{stepLabel(gs.step_name)}</span>
                        <span className="gate-stage-detail">{gs.detail}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
