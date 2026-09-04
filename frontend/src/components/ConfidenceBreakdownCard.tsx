// Priority: "show confidence computation", not just the final number. Pulls
// the exact inputs to confidence.compute() straight from the backend
// (trusted/expected counts, contradiction penalty, and per-signal status) —
// the arithmetic here is real, not re-derived client-side.
import { useFleet } from "../FleetDataContext";
import { signalLabel } from "../humanize";

function factorRow(label: string, value: number) {
  return (
    <div className="composite-factor-row" key={label}>
      <span className="composite-factor-label">{label}</span>
      <div className="composite-factor-track">
        <div className="composite-factor-fill" style={{ width: `${Math.round(value * 100)}%` }} />
      </div>
      <span className="composite-factor-value font-mono">{Math.round(value * 100)}%</span>
    </div>
  );
}

export function ConfidenceBreakdownCard() {
  const { decision } = useFleet();
  const b = decision?.confidence_breakdown;
  const c = decision?.composite_confidence;

  if (!decision || !b) return null;

  return (
    <div className="panel">
      <h2>Confidence Computation</h2>
      <div className="confidence-arith">
        ({b.trusted_count} trusted
        {b.contradiction_penalty > 0 ? ` − ${b.contradiction_penalty} contradiction` : ""}
        ) ÷ {b.expected_count} expected = <strong>{Math.round(b.confidence * 100)}%</strong>
      </div>
      <div className="confidence-signal-grid">
        {b.signals.map((s) => (
          <span key={s.signal} className={`chip ${s.trusted ? "fresh" : "invalid"}`} title={s.status ?? undefined}>
            {s.trusted ? "✓" : "✕"} {signalLabel(s.signal)}
          </span>
        ))}
      </div>

      {c && (
        <>
          <div className="trace-sub" style={{ marginTop: 16 }}>Composite Trust Score — measured, not guessed</div>
          {factorRow("Evidence Quality", c.evidence_quality)}
          {factorRow("Verifier Score", c.verifier_score)}
          {factorRow("Gate Cleanliness", c.gate_cleanliness)}
          {factorRow("Policy Compliance", c.policy_compliance)}
          {factorRow("Historical Reliability", c.historical_reliability)}
          <div className="composite-result">
            = <strong>{Math.round(c.composite * 100)}%</strong> composite
          </div>
        </>
      )}
    </div>
  );
}
