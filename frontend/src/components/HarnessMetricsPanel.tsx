// Observability metrics for the harness itself, not the fleet — aggregated
// server-side from everything already persisted (see backend/app/metrics.py),
// so there is nothing here that isn't independently derivable from Store.
import { useEffect, useState } from "react";
import { api } from "../api";
import { useFleet } from "../FleetDataContext";
import { StatCard } from "../components";
import type { HarnessMetrics } from "../types";

export function HarnessMetricsPanel() {
  const { decision } = useFleet();
  const [m, setM] = useState<HarnessMetrics | null>(null);

  useEffect(() => {
    api.metrics().then(setM).catch(() => {});
  }, [decision?.run_id]);

  if (!m) return null;

  return (
    <div className="panel">
      <h2>Harness Metrics</h2>
      <div className="metrics-grid">
        <StatCard label="Total Runs" value={String(m.total_runs)} />
        <StatCard label="Success Rate" value={`${Math.round(m.success_rate * 100)}%`}
                 tone={m.success_rate >= 0.7 ? "good" : m.success_rate >= 0.4 ? "warn" : "bad"} />
        <StatCard label="Critical Halts" value={String(m.critical_halt)} tone={m.critical_halt ? "bad" : undefined} />
        <StatCard label="Insufficient Data" value={String(m.insufficient_data)} tone={m.insufficient_data ? "warn" : undefined} />
        <StatCard label="Retries" value={String(m.retries)} tone={m.retries ? "warn" : undefined} />
        <StatCard label="Evidence Rejected" value={String(m.evidence_rejected)} />
        <StatCard label="Circuit Breaker Trips" value={String(m.circuit_breaker_trips)} tone={m.circuit_breaker_trips ? "bad" : undefined} />
        <StatCard label="Critic Rejections" value={String(m.critic_rejected)} tone={m.critic_rejected ? "warn" : undefined} />
        <StatCard label="Pending Actions" value={String(m.pending_actions)} tone={m.pending_actions ? "warn" : undefined} />
        <StatCard label="Executed Actions" value={String(m.executed_actions)} />
        <StatCard label="Avg Confidence" value={`${Math.round(m.avg_confidence * 100)}%`} />
        <StatCard label="Avg Latency" value={`${m.avg_latency_ms} ms`} />
      </div>
    </div>
  );
}
