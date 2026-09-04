// The home screen isn't a KPI dashboard — it's a control room. This panel
// renders the harness's actual pipeline (agents -> gate -> critic ->
// controller -> action) as a live flow that animates while a run is
// in flight and settles into the real outcome's color when it lands, plus
// a growing, auto-highlighting feed of the same audit events that already
// drive the Audit Logs page. No new data model — just a different lens on
// the same live poll.
import { useEffect, useRef, useState } from "react";
import { STATE_META, humanizeAudit } from "./humanize";
import { AlertTriangle } from "./icons";
import type {
  ActionRequest, AuditRecord, ControllerDecision, WorldState,
} from "./types";

type Tone = "good" | "warn" | "bad" | "idle";

function Node({
  label, value, tone, processing, sweeping,
}: { label: string; value: string; tone: Tone; processing: boolean; sweeping?: boolean }) {
  return (
    <div className={`mc-node tone-${tone}${processing ? " processing" : ""}${sweeping ? " sweeping" : ""}`}>
      <span className={`dot dot-${tone === "idle" ? "idle" : tone}`} />
      <div>
        <div className="mc-node-label">{label}</div>
        <div className="mc-node-value">{value}</div>
      </div>
    </div>
  );
}

function Connector({ flowing }: { flowing: boolean }) {
  return (
    <div className={`mc-connector${flowing ? " flowing" : ""}`}>
      <div className="mc-line" />
      <div className="mc-arrow">▾</div>
    </div>
  );
}

export function LiveExecutionPanel({
  decision, world, actions, busy, onRun,
}: {
  decision: ControllerDecision | null; world: WorldState | null;
  actions: ActionRequest[]; busy: boolean; onRun: () => void;
}) {
  const t = decision?.trace;
  const vehicleAgentTone: Tone = !decision ? "idle" : t!.agents_unavailable.includes("agent_a") ? "bad" : "good";
  const envAgentTone: Tone = !decision ? "idle" : t!.agents_unavailable.includes("agent_b") ? "bad" : "good";
  const gateTone: Tone = !decision ? "idle" : t!.excluded_evidence_ids.length ? "warn" : "good";
  const criticTone: Tone = !decision ? "idle"
    : decision.critic_rejected ? "bad"
    : decision.risk_matrix?.risk_level === "HIGH" ? "bad"
    : decision.risk_matrix?.risk_level === "MEDIUM" ? "warn" : "good";
  const controllerTone: Tone = decision ? (STATE_META[decision.controller_state].tone as Tone) : "idle";
  const actionTone: Tone = actions.length ? "warn" : "idle";

  const vehicleAgentValue = !decision ? "standing by" : vehicleAgentTone === "bad" ? "unavailable" : "reporting";
  const envAgentValue = !decision ? "standing by" : envAgentTone === "bad" ? "unavailable" : "reporting";
  const trusted = decision ? t!.evidence_snapshot.length - t!.excluded_evidence_ids.length : 0;
  const gateValue = decision ? `${trusted} trusted, ${t!.excluded_evidence_ids.length} excluded` : "standing by";
  const criticValue = !decision ? "standing by"
    : decision.critic_rejected ? "output rejected"
    : `${decision.risk_matrix?.risk_level ?? "—"} risk`;
  const controllerValue = decision ? STATE_META[decision.controller_state].headline : "standing by";
  const actionValue = actions.length ? `${actions.length} awaiting approval` : "none needed";

  const [justUpdated, setJustUpdated] = useState(false);
  const [sweepIndex, setSweepIndex] = useState(-1);
  const lastRunId = useRef<string | null>(null);
  useEffect(() => {
    if (decision && decision.run_id !== lastRunId.current) {
      lastRunId.current = decision.run_id;
      setJustUpdated(true);
      const timers: ReturnType<typeof setTimeout>[] = [
        setTimeout(() => setJustUpdated(false), 1200),
      ];

      // Choreographed reveal: the run itself is near-instant, but a judge
      // needs to actually see "agents -> gate -> risk -> decision -> action"
      // happen in order, not just a final color change.
      setSweepIndex(0);
      const STEP_MS = 220;
      [1, 2, 3, 4].forEach((stage, i) => {
        timers.push(setTimeout(() => setSweepIndex(stage), STEP_MS * (i + 1)));
      });
      timers.push(setTimeout(() => setSweepIndex(-1), STEP_MS * 5 + 150));

      return () => timers.forEach(clearTimeout);
    }
    // Keyed on run_id, not the whole decision object: FleetDataContext polls
    // every ~1.5s and hands back a fresh object for the SAME run, which would
    // otherwise re-run this effect mid-sweep and cancel the timers below via
    // the cleanup function before the animation finishes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [decision?.run_id]);

  return (
    <div className="mc-panel">
      <div className="mc-panel-head">
        <div className="mc-live-badge"><span className="mc-live-dot" />LIVE EXECUTION</div>
        <button className="mc-run-btn" disabled={busy} onClick={onRun}>{busy ? "Running…" : "Run check"}</button>
      </div>

      <div className="mc-flow">
        <div className="mc-parallel-pair">
          <Node label="Vehicle Agent" value={vehicleAgentValue} tone={vehicleAgentTone} processing={busy} sweeping={sweepIndex === 0} />
          <Node label="Environment Agent" value={envAgentValue} tone={envAgentTone} processing={busy} sweeping={sweepIndex === 0} />
        </div>
        <Connector flowing={busy || sweepIndex === 0} />
        <Node label="Trust Gate" value={gateValue} tone={gateTone} processing={busy} sweeping={sweepIndex === 1} />
        <Connector flowing={busy || sweepIndex === 1} />
        <Node label="Risk Assessment Engine" value={criticValue} tone={criticTone} processing={busy} sweeping={sweepIndex === 2} />
        <Connector flowing={busy || sweepIndex === 2} />
        <Node label="Decision Authority" value={controllerValue} tone={controllerTone} processing={busy} sweeping={sweepIndex === 3} />
        <Connector flowing={busy || sweepIndex === 3} />
        <Node label="Action Gateway" value={actionValue} tone={actionTone} processing={busy} sweeping={sweepIndex === 4} />
      </div>

      <div className={`mc-controller-line${justUpdated ? " just-updated" : ""}`}>
        {decision ? (
          <>
            <span className={`status-pill tone-${controllerTone}`}>{decision.controller_state}</span>
            <span className="mc-controller-scenario">{world?.scenario ?? "—"}</span>
          </>
        ) : (
          <span className="mc-controller-scenario">
            Ready to evaluate a fleet decision. Run a Healthy or Risk scenario to see the harness
            supervise agents, validate evidence, assess risk, and decide whether automation is safe.
          </span>
        )}
      </div>
    </div>
  );
}

const EVENT_TONE: Record<string, (p: Record<string, unknown>) => Tone> = {
  decision_made: (p) => {
    const s = p.controller_state as string;
    return s === "AUTO_OPTIMIZE" ? "good" : s === "CRITICAL_HALT" ? "bad" : "warn";
  },
  action_requested: () => "warn",
  action_approved: () => "good",
  action_rejected: () => "bad",
  action_executed: () => "good",
  agent_unavailable: () => "bad",
  critic_rejected: () => "bad",
  critic_assessed: (p) => (p.risk_level === "HIGH" ? "bad" : p.risk_level === "MEDIUM" ? "warn" : "good"),
  gate_evaluated: (p) => (Array.isArray(p.excluded_ids) && p.excluded_ids.length ? "warn" : "good"),
  security_probe: (p) => (p.blocked ? "good" : "bad"),
};

function eventTone(r: AuditRecord): Tone {
  const fn = EVENT_TONE[r.event_type];
  try { return fn ? fn(r.payload) : "idle"; } catch { return "idle"; }
}

export function LiveEventFeed({ audit }: { audit: AuditRecord[] }) {
  const seen = useRef<Set<number>>(new Set());
  const [flash, setFlash] = useState<Set<number>>(new Set());

  useEffect(() => {
    const freshIds = audit.filter((r) => !seen.current.has(r.id)).map((r) => r.id);
    const isFirstLoad = seen.current.size === 0;
    audit.forEach((r) => seen.current.add(r.id));
    if (freshIds.length && !isFirstLoad) {
      setFlash((prev) => new Set([...prev, ...freshIds]));
      const t = setTimeout(() => {
        setFlash((prev) => {
          const next = new Set(prev);
          freshIds.forEach((id) => next.delete(id));
          return next;
        });
      }, 1500);
      return () => clearTimeout(t);
    }
  }, [audit]);

  return (
    <div className="mc-panel mc-feed">
      <div className="mc-panel-head">
        <div className="mc-live-badge"><span className="mc-live-dot" />RECENT EVENTS</div>
      </div>
      <div className="mc-feed-list">
        {audit.length === 0 && <div className="mc-feed-empty">No activity yet.</div>}
        {audit.slice(0, 30).map((r) => (
          <div className={`mc-feed-row tone-${eventTone(r)}${flash.has(r.id) ? " enter" : ""}`} key={r.id}>
            <span className="mc-feed-time">
              {new Date(r.ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
            </span>
            <span className={`dot dot-${eventTone(r)}`} />
            <span className="mc-feed-text">{humanizeAudit(r)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export function MissionControlAlert({ actions }: { actions: ActionRequest[] }) {
  if (actions.length === 0) return null;
  return (
    <div className="mc-alert">
      <AlertTriangle size={15} />
      {actions.length} decision{actions.length > 1 ? "s" : ""} waiting on human approval — see below.
    </div>
  );
}
