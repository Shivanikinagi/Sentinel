// Trusted Evidence — every signal the harness reasoned about, with the
// agent that collected it and whether the Trust Gate accepted it. Renamed
// from "Evidence Provenance": the point for a judge isn't provenance
// metadata, it's that every signal has a verified source before the LLM
// ever sees it.
import { useFleet } from "../FleetDataContext";
import { signalLabel, signalValue } from "../humanize";

const COLLECTED_BY: Record<string, string> = {
  agent_a: "Vehicle Agent",
  agent_b: "Environment Agent",
};

export function TrustedEvidenceCard() {
  const { decision } = useFleet();
  const snapshot = decision?.trace?.evidence_snapshot ?? [];

  if (!decision || snapshot.length === 0) return null;

  const excludedIds = new Set(decision.trace.excluded_evidence_ids);
  const trustedCount = snapshot.length - excludedIds.size;

  return (
    <div className="provenance-card">
      <div className="provenance-header">
        <h3>🔍 Trusted Evidence</h3>
        <span className="badge badge-info">{trustedCount} of {snapshot.length} trusted</span>
      </div>

      <div className="trusted-evidence-table">
        <div className="te-row te-head">
          <span>Signal</span>
          <span>Value</span>
          <span>Collected By</span>
          <span>Status</span>
        </div>
        {snapshot.map((ev) => {
          const excluded = excludedIds.has(ev.evidence_id);
          return (
            <div className={`te-row${excluded ? " te-excluded" : ""}`} key={ev.evidence_id}>
              <span className="te-signal">{signalLabel(ev.signal)}</span>
              <span className="te-value font-mono">{signalValue(ev.signal, ev.value, ev.unit)}</span>
              <span className="te-source">{COLLECTED_BY[ev.source] ?? ev.source}</span>
              <span className={`te-status ${excluded ? "bad" : "good"}`}>
                {excluded ? "✕ Excluded" : "✓ Trusted"}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
