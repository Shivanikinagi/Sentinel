// Makes the Harness Runtime a first-class, visible thing — not just an
// implicit pipeline function. Every box maps to a real backend module (see
// `file`, shown as a tooltip); tags are scannable at a glance, the full
// sentence is one hover away for anyone who wants it.
import { ActivityIcon, ClipboardIcon, GridIcon, ShieldIcon, ZapIcon } from "../icons";

const COMPONENTS = [
  { key: "supervisor", title: "Supervisor", file: "supervisor.py", tags: ["Launch", "Retry", "Trace"],
    desc: "Starts each agent, times every stage, retries a failed Risk Assessment call, and assembles the execution trace." },
  { key: "state", title: "State Manager", file: "run_state.py", tags: ["Read", "Write", "Track"],
    desc: "RunState — the single object every stage reads and writes: evidence, confidence, completed/failed agents, decision, trace." },
  { key: "scheduler", title: "Scheduler", file: "planner.py", tags: ["Plan", "Order", "Parallel"],
    desc: "Planner decides which agents run and whether in parallel — both observers today, since their scopes are provably disjoint." },
  { key: "retry", title: "Retry Engine", file: "retry_engine.py", tags: ["Bound", "Backoff", "Recover"],
    desc: "Bounded retry around the one call that crosses a real network boundary — the Risk Assessment Engine backend." },
  { key: "policy", title: "Policy Engine", file: "policy_packs.py", tags: ["Select", "Swap", "Enforce"],
    desc: "Selects the active domain policy pack (Cold Chain, Tyre Safety, …) that the Gate, Correlation Engine, and Critic all read from." },
  { key: "trace", title: "Execution Trace", file: "schemas.DecisionStep", tags: ["Time", "Record", "Order"],
    desc: "Every stage — including retries and the 4 Trust Gate sub-stages — is timed and recorded in order." },
  { key: "memory", title: "Memory", file: "memory.py", tags: ["Trend", "Compare", "History"],
    desc: "Trend engine over Store history — tracks a signal across a vehicle's past runs instead of judging one snapshot." },
  { key: "audit", title: "Audit", file: "audit.py", tags: ["Log", "Append", "Query"],
    desc: "Append-only log of every meaningful transition, queryable end to end." },
];

const ICONS: Record<string, typeof ShieldIcon> = {
  supervisor: ActivityIcon, state: GridIcon, scheduler: ZapIcon, retry: ZapIcon,
  policy: ShieldIcon, trace: ClipboardIcon, memory: ClipboardIcon, audit: ShieldIcon,
};

export function HarnessRuntimeDiagram() {
  return (
    <div className="panel">
      <h2>Harness Runtime</h2>
      <p className="stat-sub" style={{ marginBottom: 0 }}>Everything plugs into this — not a bare pipeline.</p>
      <div className="runtime-diagram">
        {COMPONENTS.map((c) => {
          const Icon = ICONS[c.key];
          return (
            <div className="runtime-box" key={c.key} title={c.desc}>
              <div className="runtime-box-icon"><Icon size={16} /></div>
              <div className="runtime-box-title">{c.title}</div>
              <div className="runtime-box-tags">
                {c.tags.map((t) => <span className="runtime-tag" key={t}>✓ {t}</span>)}
              </div>
            </div>
          );
        })}
      </div>
      <div className="runtime-flow-note">
        Planner → Supervisor(agents → Gate → Correlation → Risk Assessment → Verifier → Controller) → Harness → Store / Gateway / Audit
      </div>
    </div>
  );
}
