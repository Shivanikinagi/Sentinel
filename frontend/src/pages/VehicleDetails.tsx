import { useFleet } from "../FleetDataContext";
import { CriticPanel, EvidencePanel } from "../components";
import { STATE_META, relativeTime, signalLabel } from "../humanize";
import { TruckIcon } from "../icons";

export default function VehicleDetails() {
  const { decision, world, technical } = useFleet();
  const sw = world?.switches;
  const state = decision?.controller_state ?? null;
  const tone = state ? STATE_META[state].tone : "idle";

  const telemetry = { ...(world?.vehicle ?? {}), ...(world?.environment ?? {}) };
  const entries = Object.entries(telemetry);

  return (
    <div className="page">
      <div className="vehicle-header panel">
        <div className="vehicle-header-left">
          <div className="panel-icon blue"><TruckIcon size={20} /></div>
          <div>
            <div className="vehicle-id">{decision?.vehicle_id ?? "TRUCK-042"}</div>
            <div className="panel-sub">Refrigerated cold-chain delivery{technical && <span className="tech-caption"> · scenario: {world?.scenario ?? "—"}</span>}</div>
          </div>
        </div>
        <div className="vehicle-header-right">
          {state && <span className={`status-pill tone-${tone}`}><span className={`dot dot-${tone}`} />{state}</span>}
          <div className="vehicle-header-time">Last check {decision ? relativeTime(decision.timestamp) : "—"}</div>
        </div>
      </div>

      <div className="panel">
        <h2>Live Telemetry{technical && <span className="tech-caption"> · raw world state</span>}</h2>
        {entries.length === 0 ? (
          <div className="empty">No telemetry yet — run a check from Simulation Lab.</div>
        ) : (
          <div className="telemetry-grid">
            {entries.map(([k, v]) => (
              <div className="telemetry-cell" key={k}>
                <div className="telemetry-label">{signalLabel(k)}</div>
                <div className="telemetry-value">{typeof v === "number" ? Math.round(v * 100) / 100 : String(v)}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="dash-grid">
        <EvidencePanel source="agent_a" d={decision} agentDown={!!sw?.agent_a_disabled} technical={technical} />
        <EvidencePanel source="agent_b" d={decision} agentDown={!!sw?.agent_b_disabled} technical={technical} />
      </div>

      <CriticPanel d={decision} technical={technical} />
    </div>
  );
}
