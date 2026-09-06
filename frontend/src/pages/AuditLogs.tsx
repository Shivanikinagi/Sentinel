import { useMemo, useState } from "react";
import { useFleet } from "../FleetDataContext";
import { PipelineStepper } from "../components";
import { humanizeAudit, relativeTime, SOURCE_META, STATE_META } from "../humanize";
import { AlertTriangle, CheckCircle, SearchIcon, XCircle } from "../icons";
import type { AuditRecord, ControllerDecision, ControllerState } from "../types";

const EVENT_TYPES = [
  "run_started", "evidence_observed", "agent_unavailable", "gate_evaluated",
  "critic_assessed", "critic_rejected", "decision_made", "action_requested",
  "action_approved", "action_rejected", "action_executed", "security_probe", "sim_triggered",
];

// Who actually performed each event, for the "actor" column — mirrors the
// pipeline stage that emits it (see supervisor.py's AuditEvent.publish calls).
const EVENT_ACTOR: Record<string, string> = {
  run_started: "Supervisor",
  evidence_observed: "Telemetry Agents",
  agent_unavailable: "Telemetry Agents",
  gate_evaluated: "Trust Gate",
  critic_assessed: "Risk Engine",
  critic_rejected: "Risk Engine",
  decision_made: "Controller",
  action_requested: "Action Gateway",
  action_approved: "Operator",
  action_rejected: "Operator",
  action_executed: "Action Gateway",
  security_probe: "Security Probe",
  sim_triggered: "Simulator",
};

// Which decision_chain step(s) this event corresponds to, so its real
// duration can be read off the same run's trace instead of guessed.
const EVENT_STEP_NAMES: Record<string, string[]> = {
  evidence_observed: ["agent_vehicle_observer", "agent_environment_observer"],
  gate_evaluated: ["trust_gate", "evidence_correlation"],
  critic_assessed: ["risk_assessment_engine"],
  critic_rejected: ["risk_assessment_engine"],
  decision_made: ["deterministic_controller"],
};

function auditActor(r: AuditRecord): string {
  if (r.event_type === "agent_unavailable") {
    const agent = String(r.payload.agent ?? "");
    return SOURCE_META[agent]?.title ?? EVENT_ACTOR[r.event_type];
  }
  return EVENT_ACTOR[r.event_type] ?? "Harness";
}

function auditDurationMs(r: AuditRecord, history: ControllerDecision[]): number | null {
  const names = EVENT_STEP_NAMES[r.event_type];
  if (!names || !r.run_id) return null;
  const d = history.find((h) => h.run_id === r.run_id);
  const steps = d?.trace.decision_chain ?? [];
  const matched = steps.filter((s) => names.includes(s.step_name));
  if (matched.length === 0) return null;
  return matched.reduce((sum, s) => sum + (s.duration_ms || 0), 0);
}

type AuditTone = "ok" | "warn" | "bad";

function auditTone(r: AuditRecord): AuditTone {
  switch (r.event_type) {
    case "agent_unavailable":
      return "warn";
    case "gate_evaluated": {
      const excluded = Array.isArray(r.payload.excluded_ids) ? r.payload.excluded_ids.length : 0;
      return excluded > 0 ? "warn" : "ok";
    }
    case "critic_assessed": {
      const level = r.payload.risk_level;
      return level === "HIGH" ? "bad" : level === "MEDIUM" ? "warn" : "ok";
    }
    case "critic_rejected":
      return "bad";
    case "decision_made": {
      const state = r.payload.controller_state as ControllerState;
      return state === "AUTO_OPTIMIZE" ? "ok" : state === "CRITICAL_HALT" ? "bad" : "warn";
    }
    case "action_rejected":
      return "bad";
    case "security_probe":
      return r.payload.blocked ? "ok" : "bad";
    default:
      return "ok";
  }
}

function ToneIcon({ tone }: { tone: AuditTone }) {
  if (tone === "ok") return <CheckCircle size={13} />;
  if (tone === "warn") return <AlertTriangle size={13} />;
  return <XCircle size={13} />;
}

function clockTime(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "—" : d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
}

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
          <div className="audit audit-tall audit-structured">
            {filtered.map((r) => {
              const tone = auditTone(r);
              const duration = auditDurationMs(r, history);
              return (
                <button
                  className={`audit-row-btn audit-row-v2 tone-${tone}${r.run_id === selectedRun ? " selected" : ""}`}
                  key={r.id} onClick={() => pick(r)} disabled={!r.run_id}
                >
                  <span className="audit-row-clock">{clockTime(r.ts)}</span>
                  <span className="audit-row-actor">{auditActor(r)}</span>
                  <span className="audit-row-text">{humanizeAudit(r)}</span>
                  <span className="audit-row-duration">{duration !== null ? `${Math.round(duration)} ms` : ""}</span>
                  <span className={`audit-row-status inline-tone tone-${tone}`}><ToneIcon tone={tone} /></span>
                  {technical && (
                    <div className="tech-caption audit-raw">
                      {r.event_type} · {r.run_id ?? "—"} · {relativeTime(r.ts)}
                    </div>
                  )}
                </button>
              );
            })}
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
                <div className="summary">{selected.risk_matrix.reasoning_summary}</div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
