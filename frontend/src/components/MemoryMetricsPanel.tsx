// Proof that state persists ACROSS runs, not just within one — the backend's
// Memory (TrendEngine), Incident Memory, and aggregate Metrics subsystems all
// read the same SQLite-backed store the current run's decision was written
// into. Kept to stat tiles, one sparkline, and a short list — no prose.
import { useEffect, useState } from "react";
import { api } from "../api";
import { useFleet } from "../FleetDataContext";
import { StatCard } from "../components";
import { Sparkline } from "../charts";
import { relativeTime } from "../humanize";
import { RefreshIcon } from "../icons";
import type { HarnessMetrics, IncidentRecord, VehicleTrend } from "../types";

const DIRECTION_LABEL: Record<string, string> = {
  rising: "rising", falling: "falling", flat: "flat", insufficient_data: "—",
};

function resolutionTone(status: string | null): "good" | "warn" | "bad" {
  if (status === "EXECUTED" || status === "APPROVED") return "good";
  if (status === "REJECTED") return "bad";
  return "warn";
}

export function MemoryMetricsPanel() {
  const { decision } = useFleet();
  const [metrics, setMetrics] = useState<HarnessMetrics | null>(null);
  const [trend, setTrend] = useState<VehicleTrend | null>(null);
  const [incidents, setIncidents] = useState<IncidentRecord[]>([]);

  useEffect(() => {
    let cancelled = false;
    const vehicleId = decision?.vehicle_id;
    Promise.all([
      api.metrics(),
      vehicleId ? api.vehicleTrend(vehicleId, "cargo_temperature", 8) : Promise.resolve(null),
      api.incidents(vehicleId, 4),
    ]).then(([m, t, i]) => {
      if (cancelled) return;
      setMetrics(m);
      setTrend(t);
      setIncidents(i);
    }).catch(() => {});
    return () => { cancelled = true; };
  }, [decision?.run_id, decision?.vehicle_id]);

  if (!metrics) return null;

  return (
    <div className="panel">
      <h2><RefreshIcon size={14} /> Memory &amp; History <span className="tech-caption"> · persisted across runs</span></h2>

      <div className="stat-grid" style={{ marginBottom: 16 }}>
        <StatCard label="Total Runs" value={String(metrics.total_runs)} />
        <StatCard label="Critical Halts" value={String(metrics.critical_halt)} tone={metrics.critical_halt ? "warn" : "good"} />
        <StatCard label="Retries Recovered" value={String(metrics.retries)} />
        <StatCard label="Circuit Trips" value={String(metrics.circuit_breaker_trips)} tone={metrics.circuit_breaker_trips ? "warn" : "good"} />
      </div>

      <div className="dash-grid">
        <div>
          <div className="panel-sub memory-subhead">
            Signal Trend{trend ? ` · ${trend.signal}` : ""}
            {trend && trend.direction !== "insufficient_data" && (
              <span className={`status-pill tone-${trend.direction === "rising" ? "warn" : "good"}`}>
                {DIRECTION_LABEL[trend.direction]}
              </span>
            )}
          </div>
          {trend && trend.points.length >= 2 ? (
            <Sparkline points={trend.points.map((p) => p.value)} width={280} height={60} />
          ) : (
            <div className="empty">Not enough runs yet.</div>
          )}
        </div>

        <div>
          <div className="panel-sub memory-subhead">Incident Memory · past halts</div>
          {incidents.length === 0 ? (
            <div className="empty">No critical halts recorded.</div>
          ) : (
            <div className="incident-mini-list">
              {incidents.map((inc) => (
                <div className="incident-mini-row" key={inc.run_id}>
                  <span className="audit-row-clock">{relativeTime(inc.timestamp)}</span>
                  <span className="audit-row-text">{inc.risk_factors[0] ?? inc.reason}</span>
                  <span className={`status-pill tone-${resolutionTone(inc.resolution_status)}`}>
                    {inc.resolution_status ?? "PENDING"}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
