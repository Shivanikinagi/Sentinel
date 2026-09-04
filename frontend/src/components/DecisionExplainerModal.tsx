import { useFleet } from "../FleetDataContext";

interface DecisionExplainerModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function DecisionExplainerModal({ isOpen, onClose }: DecisionExplainerModalProps) {
  const { decision, backend } = useFleet();

  if (!isOpen || !decision) return null;

  return (
    <div className="presenter-drawer-overlay" onClick={onClose}>
      <div className="presenter-drawer explainer-modal" onClick={(e) => e.stopPropagation()}>
        <div className="presenter-drawer-header">
          <div>
            <span className="presenter-tag">DECISION EXPLAINER</span>
            <h2>Why Was This Decision Made?</h2>
            <p>Complete transparent breakdown for Run ID: {decision.run_id}</p>
          </div>
          <button className="btn-close" onClick={onClose}>✕</button>
        </div>

        <div className="presenter-drawer-body">
          <div className="explainer-section">
            <h4>1. Final State & Confidence</h4>
            <div className="explainer-box">
              <span className={`status-pill tone-${decision.controller_state === "AUTO_OPTIMIZE" ? "good" : "bad"}`}>
                {decision.controller_state}
              </span>
              <span className="font-mono" style={{ marginLeft: "12px" }}>
                Confidence: <strong>{Math.round(decision.confidence * 100)}%</strong>
              </span>
              <p style={{ marginTop: "8px", fontSize: "12.5px" }}>{decision.reason}</p>
            </div>
          </div>

          <div className="explainer-section">
            <h4>2. LLM Critic Reasoning ({backend})</h4>
            <div className="explainer-box">
              <p><strong>Risk Level:</strong> {decision.risk_matrix?.risk_level ?? "REJECTED"}</p>
              <p><strong>Contradiction Detected:</strong> {decision.risk_matrix?.contradiction_detected ? "YES ⚠️" : "NO ✓"}</p>
              <p><strong>Reasoning Summary:</strong> {decision.risk_matrix?.reasoning_summary ?? "Output rejected by schema/verifier"}</p>
            </div>
          </div>

          <div className="explainer-section">
            <h4>3. Verifier Sub-System Status</h4>
            <div className="explainer-box">
              <p><strong>Status:</strong> {decision.trace.verifier_result?.valid ? "Passed ✅" : "Failed ❌"}</p>
              <p><strong>Reason:</strong> {decision.trace.verifier_result?.reason}</p>
            </div>
          </div>

          <div className="explainer-section">
            <h4>4. Evidence Grounding Snapshot ({decision.trace.evidence_snapshot.length} signals)</h4>
            <div className="explainer-box font-mono" style={{ fontSize: "11px" }}>
              {decision.trace.evidence_snapshot.map((ev) => (
                <div key={ev.evidence_id}>
                  • {ev.signal}: <strong>{ev.value} {ev.unit}</strong> [{ev.source}] ({ev.status})
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="presenter-drawer-footer">
          <button className="btn btn-primary" onClick={onClose}>
            Close Explainer
          </button>
        </div>
      </div>
    </div>
  );
}
