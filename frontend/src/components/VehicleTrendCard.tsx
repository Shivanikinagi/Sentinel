// Memory: judge a signal against its recent history instead of one snapshot.
// Reads from GET /vehicles/{id}/trend, which walks the vehicle's persisted
// decisions — no client-side history cap, no reset-on-reload.
import { useEffect, useState } from "react";
import { api } from "../api";
import { useFleet } from "../FleetDataContext";
import { Sparkline } from "../charts";
import { signalLabel } from "../humanize";
import type { VehicleTrend } from "../types";

const SIGNALS = ["cargo_temperature", "tyre_pressure", "tyre_temperature", "ambient_temperature"];

const DIRECTION_META: Record<VehicleTrend["direction"], { label: string; tone: string }> = {
  rising: { label: "Rising", tone: "warn" },
  falling: { label: "Falling", tone: "warn" },
  flat: { label: "Stable", tone: "good" },
  insufficient_data: { label: "Not enough runs yet", tone: "idle" },
};

export function VehicleTrendCard() {
  const { decision } = useFleet();
  const [signal, setSignal] = useState("cargo_temperature");
  const [trend, setTrend] = useState<VehicleTrend | null>(null);
  const vehicleId = decision?.vehicle_id;

  useEffect(() => {
    if (!vehicleId) return;
    api.vehicleTrend(vehicleId, signal, 10).then(setTrend).catch(() => {});
  }, [vehicleId, signal, decision?.run_id]);

  if (!vehicleId) return null;
  const meta = trend ? DIRECTION_META[trend.direction] : null;

  return (
    <div className="panel">
      <div className="trend-header">
        <h2 style={{ marginBottom: 0 }}>Signal Trend — {vehicleId}</h2>
        <select className="trend-select" value={signal} onChange={(e) => setSignal(e.target.value)}>
          {SIGNALS.map((s) => <option key={s} value={s}>{signalLabel(s)}</option>)}
        </select>
      </div>
      {!trend || trend.points.length < 2 ? (
        <div className="empty">Not enough runs yet to show a trend for {signalLabel(signal)}.</div>
      ) : (
        <>
          <Sparkline points={trend.points.map((p) => p.value)} width={320} height={60} />
          <div style={{ display: "flex", justifyContent: "space-between", marginTop: 8 }}>
            <span className={`status-pill tone-${meta?.tone}`}>{meta?.label}</span>
            <span className="font-mono text-muted">
              {trend.points.length} runs · Δ {trend.delta ?? 0}
            </span>
          </div>
        </>
      )}
    </div>
  );
}
