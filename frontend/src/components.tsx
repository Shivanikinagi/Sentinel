import { useState, type ReactNode } from "react";
import {
  AlertTriangle, CheckCircle, CloudIcon, InfoIcon, ShieldIcon, TruckIcon,
  XCircle, ZapIcon,
} from "./icons";
import {
  actionTypeLabel, humanizeAudit, humanizeGateNote, humanizeReason,
  relativeTime, riskFactorLabel, signalLabel, signalValue, SOURCE_META, STATE_META,
} from "./humanize";
import type {
  ActionRequest, AuditRecord, ControllerDecision, Evidence, ProbeResult,
} from "./types";

const FRESHNESS_LABEL: Record<string, string> = {
  fresh: "up to date", stale: "getting old", invalid: "too old",
};

function truncate(s: string, max: number): string {
  return s.length > max ? `${s.slice(0, max)}…` : s;
}

export function StatCard({
  label, value, sub, tone, icon,
}: {
  label: string; value: string; sub?: string; tone?: "good" | "warn" | "bad"; icon?: ReactNode;
}) {
  return (
    <div className="stat-card">
      <div className="stat-top">
        <span className="stat-label">{label}</span>
        {icon && <span className="stat-icon">{icon}</span>}
      </div>
      <div className={`stat-value${tone ? ` tone-${tone}` : ""}`}>{value}</div>
      {sub && <div className="stat-sub">{sub}</div>}
    </div>
  );
}

export function ControllerBanner({
  d, technical,
}: {
  d: ControllerDecision | null;
  technical: boolean;
}) {
  if (!d) {
    return (
      <div className="banner idle">
        <div className="state-icon"><InfoIcon size={22} /></div>
        <div>
          <div className="state">No check run yet</div>
          <div className="reason">Press "Run check" to see the truck's current status.</div>
        </div>
      </div>
    );
  }
  const meta = STATE_META[d.controller_state];
  const Icon = d.controller_state === "AUTO_OPTIMIZE" ? CheckCircle
    : d.controller_state === "CRITICAL_HALT" ? XCircle : AlertTriangle;
  const confLabel = d.confidence >= 0.85 ? "High" : d.confidence >= 0.5 ? "Medium" : "Low";

  return (
    <div className={`banner ${d.controller_state}`}>
      <div className="banner-main">
        <div className="state-icon"><Icon size={26} /></div>
        <div>
          <div className="state">{meta.headline}</div>
          <div className="reason">{humanizeReason(d.reason)}</div>
          {technical && (
            <div className="tech-caption">
              {d.controller_state} · {d.reason} · run {d.run_id}
            </div>
          )}
        </div>
      </div>
      <div className="meta">
        <div>
          <div className="k">Confidence</div>
          <div className="v">{confLabel} <span className="v-sub">{(d.confidence * 100).toFixed(0)}%</span></div>
        </div>
        <div>
          <div className="k">Truck</div>
          <div className="v">{d.vehicle_id}</div>
        </div>
      </div>
    </div>
  );
}

function EvRow({ ev, excluded, technical }: { ev: Evidence; excluded: boolean; technical: boolean }) {
  return (
    <div className={`evrow ${excluded ? "excluded" : ""}`}>
      <span className="sig">{signalLabel(ev.signal)}</span>
      <span className="evrow-right">
        <span className="val">{signalValue(ev.signal, ev.value, ev.unit)}</span>
        <span className={`chip ${ev.status}`}>
          {technical ? ev.status : FRESHNESS_LABEL[ev.status]}
        </span>
      </span>
    </div>
  );
}

export function EvidencePanel({
  source, d, agentDown, technical,
}: {
  source: "agent_a" | "agent_b";
  d: ControllerDecision | null;
  agentDown: boolean;
  technical: boolean;
}) {
  const meta = SOURCE_META[source];
  const snapshot = d?.trace.evidence_snapshot ?? [];
  const rows = snapshot.filter((e) => e.source === source);
  const excludedIds = new Set(d?.trace.excluded_evidence_ids ?? []);
  return (
    <div className="panel">
      <div className="panel-head">
        <TruckIconOrCloud source={source} />
        <div>
          <h2>{meta.title}</h2>
          <div className="panel-sub">{meta.sub}{technical && <span className="tech-caption"> · {source}</span>}</div>
        </div>
      </div>
      {agentDown ? (
        <div className="agent-down"><AlertTriangle size={14} /> Lost connection — no data this check</div>
      ) : rows.length === 0 ? (
        <div className="empty">No data yet.</div>
      ) : (
        rows.map((ev) => (
          <EvRow key={ev.evidence_id} ev={ev} excluded={excludedIds.has(ev.evidence_id)} technical={technical} />
        ))
      )}
    </div>
  );
}

function TruckIconOrCloud({ source }: { source: "agent_a" | "agent_b" }) {
  return (
    <div className={`panel-icon ${source === "agent_a" ? "blue" : "teal"}`}>
      {source === "agent_a" ? <TruckIcon size={16} /> : <CloudIcon size={16} />}
    </div>
  );
}

const RISK_LABEL: Record<string, string> = { LOW: "Low risk", MEDIUM: "Some risk", HIGH: "High risk" };

export function CriticPanel({ d, technical }: { d: ControllerDecision | null; technical: boolean }) {
  return (
    <div className="panel">
      <h2>AI Risk Assessment{technical && <span className="tech-caption"> · Risk Assessment Engine</span>}</h2>
      {!d ? (
        <div className="empty">—</div>
      ) : d.critic_rejected ? (
        <div className="rejected-box">
          <AlertTriangle size={15} /> The AI's answer didn't come back in a valid
          format, so it was ignored and we played it safe.
        </div>
      ) : d.risk_matrix ? (
        <>
          <span className={`risk-tag risk-${d.risk_matrix.risk_level}`}>
            {RISK_LABEL[d.risk_matrix.risk_level]}
            {technical && ` (${d.risk_matrix.risk_level})`}
          </span>
          {d.risk_matrix.contradiction_detected && (
            <div className="contradiction">
              <AlertTriangle size={14} /> Two readings don't add up — possible equipment issue
            </div>
          )}
          <div className="factors">
            {d.risk_matrix.risk_factors.map((f) => (
              <span className="factor" key={f} title={technical ? f : undefined}>{riskFactorLabel(f)}</span>
            ))}
          </div>
          <div className="summary">{d.risk_matrix.reasoning_summary}</div>
        </>
      ) : (
        <div className="empty">No assessment yet.</div>
      )}
    </div>
  );
}

export function PendingActions({
  actions, onApprove, onReject, technical,
}: {
  actions: ActionRequest[];
  onApprove: (id: string) => void;
  onReject: (id: string) => void;
  technical: boolean;
}) {
  return (
    <div className="panel">
      <h2>Needs Your Approval{technical && <span className="tech-caption"> · Action Gateway</span>}</h2>
      {actions.length === 0 ? (
        <div className="empty">Nothing waiting on you right now.</div>
      ) : (
        <>
          <div className="stepper" style={{ marginBottom: 14 }}>
            <Step label="Critical Halt" status="bad" value="Automation stopped" />
            <span className="arrow">→</span>
            <Step label="Human Approval Required" status="warn" value={`${actions.length} pending`} />
            <span className="arrow">→</span>
            <Step label="Escalation Record" status="idle" value="created on approval" />
          </div>
          {actions.map((a) => (
            <div className="action-card" key={a.action_id}>
              <div className="title">{actionTypeLabel(a.action_type)}</div>
              <div className="why">{humanizeReason(a.reason)}</div>
              {technical && <div className="tech-caption">{a.action_type} · tier {a.tier} · {a.reason}</div>}
              <div className="btns">
                <button className="ok" onClick={() => onApprove(a.action_id)}>
                  <CheckCircle size={14} /> Approve
                </button>
                <button className="danger" onClick={() => onReject(a.action_id)}>
                  <XCircle size={14} /> Reject
                </button>
              </div>
            </div>
          ))}
        </>
      )}
    </div>
  );
}

type StepStatus = "ok" | "warn" | "bad" | "idle";

function Step({ label, sub, value, status }: { label: string; sub?: string; value: string; status: StepStatus }) {
  return (
    <div className={`step ${status}`}>
      <div className="step-label">{label}{sub ? <span className="tech-caption"> · {sub}</span> : null}</div>
      <div className="step-value">{value}</div>
    </div>
  );
}

export function PipelineStepper({ d, technical }: { d: ControllerDecision; technical: boolean }) {
  const t = d.trace;
  const trusted = t.evidence_snapshot.length - t.excluded_evidence_ids.length;
  const agentStatus: StepStatus = t.agents_unavailable.length ? "bad" : "ok";
  const gateStatus: StepStatus = t.excluded_evidence_ids.length ? "warn" : "ok";
  const criticStatus: StepStatus = d.critic_rejected ? "bad"
    : d.risk_matrix?.risk_level === "HIGH" ? "warn" : "ok";
  const ctrlStatus: StepStatus =
    d.controller_state === "AUTO_OPTIMIZE" ? "ok"
      : d.controller_state === "CRITICAL_HALT" ? "bad" : "warn";

  return (
    <div className="stepper">
      <Step label="Sensors" sub={technical ? "Agents" : undefined}
           value={`${t.agents_reporting.length} reporting`} status={agentStatus} />
      <span className="arrow">→</span>
      <Step label="Data Check" sub={technical ? "Gate" : undefined}
           value={`${trusted} trusted / ${t.excluded_evidence_ids.length} ignored`} status={gateStatus} />
      <span className="arrow">→</span>
      <Step label="AI Review" sub={technical ? "Critic" : undefined}
           value={d.critic_rejected ? "rejected" : RISK_LABEL[d.risk_matrix?.risk_level ?? ""] ?? "—"}
           status={criticStatus} />
      <span className="arrow">→</span>
      <Step label="Decision" sub={technical ? "Controller" : undefined}
           value={STATE_META[d.controller_state].headline} status={ctrlStatus} />
      <span className="arrow">→</span>
      <Step label="Next Step" sub={technical ? "Action" : undefined}
           value={d.escalation_id ? "sent for approval" : "none needed"}
           status={d.escalation_id ? "bad" : "idle"} />
    </div>
  );
}

export function TraceView({ d, technical }: { d: ControllerDecision | null; technical: boolean }) {
  if (!d) return null;
  const t = d.trace;
  const excluded = t.evidence_snapshot.filter((e) => t.excluded_evidence_ids.includes(e.evidence_id));
  return (
    <div className="panel">
      <h2>What happened</h2>
      <PipelineStepper d={d} technical={technical} />

      {excluded.length > 0 && (
        <>
          <div className="trace-sub">Data we didn't use</div>
          {excluded.map((e) => (
            <div className="evrow excluded" key={e.evidence_id}>
              <span className="sig">{signalLabel(e.signal)}</span>
              <span className="evrow-right">
                <span className="val">{signalValue(e.signal, e.value, e.unit)}</span>
                <span className={`chip ${e.status}`}>{technical ? e.status : FRESHNESS_LABEL[e.status]}</span>
              </span>
            </div>
          ))}
        </>
      )}

      <div className="trace-sub">Why</div>
      <ul className="trace-notes">
        {t.gate_notes.map((n, i) => (
          <li key={i}>
            {humanizeGateNote(n)}
            {technical && <div className="tech-caption">{n}</div>}
          </li>
        ))}
        {t.gate_notes.length === 0 && <li>All data was trusted — nothing was ignored.</li>}
      </ul>
    </div>
  );
}

export function SecurityProbe({
  result, onProbe, technical,
}: {
  result: ProbeResult | null;
  onProbe: () => void;
  technical: boolean;
}) {
  const [showDetails, setShowDetails] = useState(false);
  const expanded = showDetails || technical;
  return (
    <div className="panel">
      <h2>Security Check{technical && <span className="tech-caption"> · Authorization Boundary</span>}</h2>
      <button className="warn" onClick={onProbe} style={{ marginBottom: 10 }}>
        <ZapIcon size={13} /> Test the safety lock
      </button>
      {!result ? (
        <div className="empty">
          Checks that the AI can never trigger a real action by itself.
        </div>
      ) : (
        <>
          <div className={result.blocked ? "probe-ok" : "probe-bad"}>
            {result.blocked ? <CheckCircle size={16} /> : <XCircle size={16} />}
            {result.blocked
              ? "Passed — the AI has no way to act on its own"
              : "Failed — see details below"}
          </div>
          {!expanded ? (
            <button className="link-btn" onClick={() => setShowDetails(true)}>
              Show how we tested this
            </button>
          ) : (
            <div className="probe-list">
              {result.attempts.map((a, i) => (
                <div className="probe-row" key={i}>
                  <span className={`probe-tag ${a.outcome === "blocked" ? "b" : "x"}`}>
                    {a.outcome === "blocked" ? "blocked" : "exposed"}
                  </span>
                  <span className="probe-vec">
                    {technical ? a.vector : "Tried to trigger an action directly"}
                  </span>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}

export function AuditLog({ records, technical }: { records: AuditRecord[]; technical: boolean }) {
  return (
    <div className="panel">
      <h2><ShieldIcon size={13} /> Activity Log</h2>
      <div className="audit">
        {records.map((r) => (
          <div className="row" key={r.id}>
            <span className="audit-text">{humanizeAudit(r)}</span>
            <span className="audit-time">{relativeTime(r.ts)}</span>
            {technical && (
              <div className="tech-caption audit-raw">
                {r.event_type}: {truncate(JSON.stringify(r.payload), 160)}
              </div>
            )}
          </div>
        ))}
        {records.length === 0 && <div className="empty">No activity yet.</div>}
      </div>
    </div>
  );
}
