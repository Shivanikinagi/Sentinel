// Per-signal trust rate across every run recorded so far — real counts from
// each decision's evidence_snapshot / excluded_evidence_ids, not a single
// run's snapshot.
import { useFleet } from "../FleetDataContext";
import { BarMini } from "../charts";
import { signalLabel } from "../humanize";

export function SensorReliabilityCard() {
  const { history } = useFleet();

  const stats = new Map<string, { trusted: number; total: number }>();
  history.forEach((d) => {
    const excluded = new Set(d.trace.excluded_evidence_ids);
    d.trace.evidence_snapshot.forEach((e) => {
      const s = stats.get(e.signal) ?? { trusted: 0, total: 0 };
      s.total += 1;
      if (!excluded.has(e.evidence_id)) s.trusted += 1;
      stats.set(e.signal, s);
    });
  });

  const items = [...stats.entries()]
    .map(([signal, s]) => ({
      label: signalLabel(signal),
      value: s.total ? Math.round((s.trusted / s.total) * 100) : 100,
    }))
    .sort((a, b) => b.value - a.value);

  return (
    <div className="panel">
      <h2>Sensor Reliability</h2>
      {items.length === 0 ? (
        <div className="empty">Run a few checks to see per-sensor trust rates.</div>
      ) : (
        <BarMini
          items={items.map((it) => ({
            ...it,
            color: it.value >= 95 ? "var(--emerald)" : it.value >= 80 ? "var(--amber)" : "var(--rose)",
          }))}
          formatValue={(v) => `${v}%`}
        />
      )}
    </div>
  );
}
