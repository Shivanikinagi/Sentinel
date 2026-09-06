import { useFleet } from "../FleetDataContext";
import { CriticPanel, EvidencePanel, StatCard } from "../components";
import { Sparkline } from "../charts";
import { STATE_META, SOURCE_META, relativeTime, signalLabel } from "../humanize";
import { TruckIcon } from "../icons";

function formatLatency(seconds: number): string {
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  return `${Math.round(seconds / 60)}m`;
}

export default function VehicleDetails() {
  const { decision, history, world, technical } = useFleet();
  const sw = world?.switches;
  const state = decision?.controller_state ?? null;
  const tone = state ? STATE_META[state].tone : "idle";

  const telemetry = { ...(world?.vehicle ?? {}), ...(world?.environment ?? {}) };
  const entries = Object.entries(telemetry);

  const trustedCount = decision ? decision.trace.evidence_snapshot.length - decision.trace.excluded_evidence_ids.length : 0;
  const totalSignals = decision?.trace.evidence_snapshot.length ?? 0;
  const rejectedCount = totalSignals - trustedCount;
  const freshnessPct = totalSignals ? Math.round((trustedCount / totalSignals) * 100) : 0;
  const gateStatus = decision ? (decision.trace.excluded_evidence_ids.length ? "warn" : "good") : undefined;

  const confidenceSeries = [...history].reverse().map((d) => d.confidence);

  const avgLatencySeconds = totalSignals
    ? decision!.trace.evidence_snapshot.reduce((sum, e) => sum + e.age_seconds, 0) / totalSignals
    : 0;
  const dataSources = decision?.trace.agents_reporting.map((a) => SOURCE_META[a]?.title ?? a).join(" + ");

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

      <div className="stat-grid">
        <StatCard label="Trust Gate" value={gateStatus === "good" ? "Clean" : gateStatus === "warn" ? "Excluded" : "—"}
                 tone={gateStatus as "good" | "warn" | undefined} sub={decision ? `${trustedCount}/${totalSignals} trusted` : "no run yet"} />
        <StatCard label="Evidence Freshness" value={decision ? `${freshnessPct}%` : "—"}
                 tone={freshnessPct === 100 ? "good" : freshnessPct >= 70 ? "warn" : freshnessPct ? "bad" : undefined} />
        <StatCard label="Confidence" value={decision ? `${Math.round(decision.confidence * 100)}%` : "—"}
                 tone={decision ? (decision.confidence >= 0.85 ? "good" : decision.confidence >= 0.5 ? "warn" : "bad") : undefined} />
        <StatCard label="Policy Pack" value={decision?.policy_pack ?? "—"} />
      </div>

      <div className="panel">
        <h2>Confidence History{technical && <span className="tech-caption"> · last {confidenceSeries.length} runs</span>}</h2>
        {confidenceSeries.length >= 2 ? (
          <Sparkline points={confidenceSeries} width={480} height={70} />
        ) : (
          <div className="empty">Run a few checks to see a trend — last 30 minutes will plot here.</div>
        )}
        <div className="telemetry-grid" style={{ marginTop: 14 }}>
          <div className="telemetry-cell">
            <div className="telemetry-label">Sensor Latency</div>
            <div className="telemetry-value">{decision ? formatLatency(avgLatencySeconds) : "—"}</div>
          </div>
          <div className="telemetry-cell">
            <div className="telemetry-label">Last Refresh</div>
            <div className="telemetry-value">{decision ? relativeTime(decision.timestamp) : "—"}</div>
          </div>
          <div className="telemetry-cell">
            <div className="telemetry-label">Data Source</div>
            <div className="telemetry-value" style={{ fontSize: 14 }}>{dataSources || "—"}</div>
          </div>
          <div className="telemetry-cell">
            <div className="telemetry-label">Trusted / Rejected</div>
            <div className="telemetry-value">
              <span className="inline-tone tone-good">{trustedCount}</span>
              {" / "}
              <span className={`inline-tone ${rejectedCount ? "tone-bad" : "tone-good"}`}>{rejectedCount}</span>
            </div>
          </div>
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
