import { useMemo, useState } from "react";
import { useFleet } from "../FleetDataContext";
import { PipelineStepper } from "../components";
import { humanizeAudit, relativeTime, STATE_META } from "../humanize";
import { SearchIcon } from "../icons";
import type { AuditRecord } from "../types";

const EVENT_TYPES = [
  "run_started", "evidence_observed", "agent_unavailable", "gate_evaluated",
  "critic_assessed", "critic_rejected", "decision_made", "action_requested",
  "action_approved", "action_rejected", "action_executed", "security_probe", "sim_triggered",
];

export default function AuditLogs() {
  const { audit, history, technical } = useFleet();
  const [query, setQuery] = useState("");
  const [eventType, setEventType] = useState("");
  const [selectedRun, setSelectedRun] = useState<string | null>(null);

  const filtered = useMemo(() => {
    return audit.filter((r) => {
      if (eventType && r.event_type !== eventType) return false;
      if (query && !humanizeAudit(r).toLowerCase().includes(query.toLowerCase())) return false;
      return true;
    });
  }, [audit, query, eventType]);

  const selected = history.find((d) => d.run_id === selectedRun) ?? history[0] ?? null;

  const pick = (r: AuditRecord) => {
    if (r.run_id) setSelectedRun(r.run_id);
  };

  return (
    <div className="page">
      <div className="panel">
        <div className="audit-filters">
          <div className="topbar-search" style={{ maxWidth: 320 }}>
            <SearchIcon size={14} />
            <input placeholder="Search activity…" value={query} onChange={(e) => setQuery(e.target.value)} />
          </div>
          <select className="select" value={eventType} onChange={(e) => setEventType(e.target.value)}>
            <option value="">All events</option>
            {EVENT_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
          <span className="panel-sub">{filtered.length} of {audit.length} records</span>
        </div>
      </div>

      <div className="audit-grid">
        <div className="panel">
          <h2>Audit Trail{technical && <span className="tech-caption"> · append-only</span>}</h2>
          <div className="audit audit-tall">
            {filtered.map((r) => (
              <button
                className={`row audit-row-btn${r.run_id === selectedRun ? " selected" : ""}`}
                key={r.id} onClick={() => pick(r)} disabled={!r.run_id}
              >
                <span className="audit-text">{humanizeAudit(r)}</span>
                <span className="audit-time">{relativeTime(r.ts)}</span>
                {technical && (
                  <div className="tech-caption audit-raw">
                    {r.event_type} · {r.run_id ?? "—"}
                  </div>
                )}
              </button>
            ))}
            {filtered.length === 0 && <div className="empty">No matching activity.</div>}
          </div>
        </div>

        <div className="panel">
          <h2>Decision Details{technical && selected && <span className="tech-caption"> · run {selected.run_id}</span>}</h2>
          {!selected ? (
            <div className="empty">Select a record with a run to inspect its decision.</div>
          ) : (
            <>
              <div className={`mini-banner tone-${STATE_META[selected.controller_state].tone}`}>
                <div className="mini-banner-state">{STATE_META[selected.controller_state].headline}</div>
                <div className="mini-banner-reason">{selected.reason}</div>
              </div>
              <PipelineStepper d={selected} technical={technical} />
              {selected.risk_matrix && (
                <div className="summary" style={{ marginTop: 12 }}>{selected.risk_matrix.reasoning_summary}</div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
