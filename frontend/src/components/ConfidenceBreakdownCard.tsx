// Priority: "show confidence computation", not just the final number. Pulls
// the exact inputs to confidence.compute() straight from the backend
// (trusted/expected counts, contradiction penalty, and per-signal status) —
// the arithmetic here is real, not re-derived client-side.
import { useFleet } from "../FleetDataContext";
import { signalLabel } from "../humanize";

export function ConfidenceBreakdownCard() {
  const { decision } = useFleet();
  const b = decision?.confidence_breakdown;

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
    </div>
  );
}
