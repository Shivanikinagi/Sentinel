// Incident Memory — distinct from Memory (VehicleTrendCard's routine signal
// history). This answers "what went wrong, and was it resolved?" not "is a
// signal drifting?". Reads GET /incidents, a join over decisions + actions
// that already exist — nothing new is persisted for this view.
import { useEffect, useState } from "react";
import { api } from "../api";
import { useFleet } from "../FleetDataContext";
import { relativeTime, riskFactorLabel } from "../humanize";
import type { IncidentRecord } from "../types";

const STATUS_TONE: Record<string, string> = {
  PENDING_APPROVAL: "warn", APPROVED: "good", EXECUTED: "good", REJECTED: "bad",
};

const STATUS_LABEL: Record<string, string> = {
  PENDING_APPROVAL: "Awaiting Approval", APPROVED: "Approved", EXECUTED: "Resolved", REJECTED: "Rejected",
};

export function IncidentMemoryPanel() {
  const { decision } = useFleet();
  const [incidents, setIncidents] = useState<IncidentRecord[]>([]);

  useEffect(() => {
    api.incidents(decision?.vehicle_id, 10).then(setIncidents).catch(() => {});
  }, [decision?.run_id, decision?.vehicle_id]);

  return (
    <div className="panel">
      <h2>Incident Memory<span className="tech-caption"> · past CRITICAL_HALTs, not routine trend</span></h2>
      {incidents.length === 0 ? (
        <div className="empty">No incidents recorded — every run so far has been clean.</div>
      ) : (
        <div className="incident-list">
          {incidents.map((inc) => (
            <div className="incident-row" key={inc.run_id}>
              <div className="incident-row-top">
                <span className="font-mono text-muted">{relativeTime(inc.timestamp)}</span>
                <span className={`status-pill tone-${STATUS_TONE[inc.resolution_status ?? ""] ?? "idle"}`}>
                  {STATUS_LABEL[inc.resolution_status ?? ""] ?? "No Action"}
                </span>
              </div>
              <div className="incident-reason">{inc.reason}</div>
              <div className="incident-factors">
                {inc.risk_factors.slice(0, 3).map((f) => (
                  <span className="factor" key={f}>{riskFactorLabel(f)}</span>
                ))}
              </div>
              {inc.resolved_by && (
                <div className="tech-caption">resolved by {inc.resolved_by}</div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
