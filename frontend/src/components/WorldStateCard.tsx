// Deliberately distinct from the Evidence panels: "World State" is the raw
// ground truth (world.py) — nothing gated, graded, or provenance-checked yet.
// "Evidence" is what the agents reported AFTER the Trust Gate ran. Keeping
// these two visually separate is the point: it's what makes clear the gate
// does real work between one and the other.
import { useFleet } from "../FleetDataContext";
import { signalLabel, signalValue } from "../humanize";

const UNITS: Record<string, string> = {
  cargo_temperature: "celsius", tyre_pressure: "psi", tyre_temperature: "celsius",
  cooling_status: "state", vehicle_speed: "kmh", ambient_temperature: "celsius",
  weather_severity: "index", traffic_level: "index", dwell_minutes: "minutes",
};

export function WorldStateCard() {
  const { world } = useFleet();
  if (!world) return null;

  const rows = [
    ...Object.entries(world.vehicle).filter(([k]) => k !== "vehicle_id"),
    ...Object.entries(world.environment),
  ];

  return (
    <div className="panel">
      <h2>World State<span className="tech-caption"> · raw ground truth, pre-gate</span></h2>
      <div className="world-state-grid">
        {rows.map(([signal, value]) => (
          <div className="world-state-cell" key={signal}>
            <span className="world-state-signal">{signalLabel(signal)}</span>
            <span className="world-state-value">{signalValue(signal, value as number, UNITS[signal] ?? "")}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
