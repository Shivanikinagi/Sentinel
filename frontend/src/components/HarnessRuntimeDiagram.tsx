// Makes the Harness Runtime a first-class, visible thing — not just an
// implicit pipeline function. Every box here maps to a real backend module
// (see the file comment on each), not a marketing label.
import { ActivityIcon, ClipboardIcon, GridIcon, ShieldIcon, ZapIcon } from "../icons";

const COMPONENTS = [
  { key: "supervisor", title: "Supervisor", file: "supervisor.py",
    desc: "Starts each agent, times every stage, retries a failed Risk Assessment call, and assembles the execution trace." },
  { key: "state", title: "State Manager", file: "run_state.py",
    desc: "RunState — the single object every stage reads and writes: evidence, confidence, completed/failed agents, decision, trace." },
  { key: "scheduler", title: "Scheduler", file: "planner.py",
    desc: "Planner decides which agents run and whether in parallel — both observers today, since their scopes are provably disjoint." },
  { key: "retry", title: "Retry Engine", file: "retry_engine.py",
    desc: "Bounded retry around the one call that crosses a real network boundary — the Risk Assessment Engine backend." },
  { key: "policy", title: "Policy Engine", file: "policy_packs.py",
    desc: "Selects the active domain policy pack (Cold Chain, Tyre Safety, …) that the Gate, Correlation Engine, and Critic all read from." },
  { key: "trace", title: "Execution Trace", file: "schemas.DecisionStep",
    desc: "Every stage — including retries and the 4 Trust Gate sub-stages — is timed and recorded in order." },
  { key: "memory", title: "Memory", file: "memory.py",
    desc: "Trend engine over Store history — tracks a signal across a vehicle's past runs instead of judging one snapshot." },
  { key: "audit", title: "Audit", file: "audit.py", desc: "Append-only log of every meaningful transition, queryable end to end." },
];

const ICONS: Record<string, typeof ShieldIcon> = {
  supervisor: ActivityIcon, state: GridIcon, scheduler: ZapIcon, retry: ZapIcon,
  policy: ShieldIcon, trace: ClipboardIcon, memory: ClipboardIcon, audit: ShieldIcon,
};

export function HarnessRuntimeDiagram() {
  return (
    <div className="panel">
      <h2>Harness Runtime</h2>
      <p className="stat-sub" style={{ marginBottom: 0 }}>
        Everything else — agents, gate, critic, verifier, controller, action gateway — plugs into this runtime.
        It is what makes this a harness, not just a pipeline.
      </p>
      <div className="runtime-diagram">
        {COMPONENTS.map((c) => {
          const Icon = ICONS[c.key];
          return (
            <div className="runtime-box" key={c.key}>
              <div className="runtime-box-title"><Icon size={13} /> {c.title}</div>
              <div className="runtime-box-desc">{c.desc}</div>
            </div>
          );
        })}
      </div>
      <div className="runtime-flow-note">
        Planner → Supervisor(agents → Trust Gate → Correlation → Risk Assessment Engine
        [retry + circuit breaker] → Verifier → Deterministic Controller) → Harness
        (persists evidence + decision, requests an action on CRITICAL_HALT) → Store / Action Gateway / Audit
      </div>
    </div>
  );
}
