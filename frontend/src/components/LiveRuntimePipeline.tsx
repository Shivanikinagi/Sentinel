// The Live Runtime Pipeline — the single visual that has to make a judge
// understand, without narration, that evidence collection, trust
// verification, LLM reasoning, and the final decision are four separate,
// independently-checked stages. Every stage's text is derived straight from
// this run's real trace.decision_chain (see backend/app/supervisor.py) — the
// choreographed reveal only controls WHEN each stage's real outcome appears,
// never fabricates one.
import { useEffect, useRef, useState } from "react";
import { useFleet } from "../FleetDataContext";
import { RefreshIcon } from "../icons";
import type { ControllerDecision, DecisionStep } from "../types";

type StageStatus = "waiting" | "running" | "passed" | "warned" | "rejected";

interface StageView {
  key: string;
  label: string;
  status: StageStatus;
  durationMs: number | null;
  detail: string;
  loop?: boolean;
}

const STAGE_ORDER = [
  "agent_vehicle_observer",
  "agent_environment_observer",
  "trust_gate",
  "evidence_correlation",
  "risk_assessment_engine",
  "verifier_subsystem",
  "deterministic_controller",
  "audit",
] as const;

const STAGE_TITLES: Record<string, string> = {
  agent_vehicle_observer: "Vehicle Agent",
  agent_environment_observer: "Environment Agent",
  trust_gate: "Trust Gate",
  evidence_correlation: "Evidence Correlation",
  risk_assessment_engine: "Risk Assessment Engine (LLM)",
  verifier_subsystem: "Verifier",
  deterministic_controller: "Decision Authority",
  audit: "Audit",
};

const STATUS_LABEL: Record<StageStatus, string> = {
  waiting: "Waiting",
  running: "Running…",
  passed: "✓ Passed",
  warned: "⚠ Passed",
  rejected: "✕ Rejected",
};

const VERIFIER_CHECK_LABELS: Record<string, string> = {
  self_consistency: "Self-Consistency Check",
  evidence_grounding: "Evidence Grounding",
  contradiction_verification: "Contradiction Validation",
};

function findStep(chain: DecisionStep[], name: string): DecisionStep | undefined {
  return chain.find((s) => s.step_name === name);
}

function leadingCount(detail: string | undefined): number {
  const m = detail?.match(/^(\d+)/);
  return m ? Number(m[1]) : 0;
}

function statusOf(step: DecisionStep): StageStatus {
  return step.status === "OK" ? "passed" : step.status === "WARNING" ? "warned" : "rejected";
}

/** Real detail + status for one stage, built entirely from this run's trace. */
function buildStage(key: string, d: ControllerDecision, auditCount: number): { status: StageStatus; durationMs: number | null; detail: string; loop?: boolean } {
  const chain = d.trace.decision_chain ?? [];
  const step = findStep(chain, key);

  if (key === "agent_vehicle_observer" || key === "agent_environment_observer") {
    if (!step) return { status: "rejected", durationMs: null, detail: "Never dispatched this run." };
    if (step.status === "FAILED") {
      return { status: "rejected", durationMs: step.duration_ms, detail: "Lost connection — no signals collected this run." };
    }
    const kind = key === "agent_vehicle_observer" ? "vehicle" : "environment";
    const count = step.detail.match(/(\d+) signals/)?.[1] ?? "0";
    return { status: "passed", durationMs: step.duration_ms, detail: `Collected ${count} ${kind} telemetry signal${count === "1" ? "" : "s"}.` };
  }

  if (key === "trust_gate") {
    if (!step) return { status: "waiting", durationMs: null, detail: "Standing by." };
    const gs = d.trace.gate_stage_results ?? [];
    const trusted = d.trace.evidence_snapshot.length - d.trace.excluded_evidence_ids.length;
    const stale = leadingCount(gs.find((s) => s.step_name === "freshness_checker")?.detail);
    const wrongSource = leadingCount(gs.find((s) => s.step_name === "provenance_checker")?.detail);
    const dupes = leadingCount(gs.find((s) => s.step_name === "evidence_normalizer")?.detail);
    return {
      status: statusOf(step),
      durationMs: step.duration_ms,
      detail: `${trusted} trusted  ·  ${stale} stale  ·  ${wrongSource} wrong source  ·  ${dupes} duplicate${dupes === 1 ? "" : "s"}`,
    };
  }

  if (key === "evidence_correlation") {
    if (!step) return { status: "waiting", durationMs: null, detail: "Standing by." };
    const conflicts = leadingCount(step.detail);
    return {
      status: statusOf(step),
      durationMs: step.duration_ms,
      detail: conflicts > 0
        ? `Found ${conflicts} physical contradiction${conflicts === 1 ? "" : "s"} between trusted signals.`
        : "No contradictions between trusted signals.",
    };
  }

  if (key === "risk_assessment_engine") {
    if (!step) return { status: "waiting", durationMs: null, detail: "Standing by." };
    if (step.status === "FAILED") {
      return { status: "rejected", durationMs: step.duration_ms, detail: "The AI's output did not come back in a valid format — discarded." };
    }
    const risk = d.risk_matrix?.risk_level ?? "—";
    return { status: "passed", durationMs: step.duration_ms, detail: `Assessed risk as ${risk}. This is a recommendation only — it decides nothing.` };
  }

  if (key === "verifier_subsystem") {
    if (!step) return { status: "waiting", durationMs: null, detail: "Standing by." };
    // `step` is always the FIRST verifier_subsystem entry in the chain, but a
    // feedback loop replaces it with a later verifier_subsystem_recheck — so
    // status/duration must come from the run's final verifier_result, not
    // this possibly-superseded step.
    const v = d.trace.verifier_result;
    const recheckStep = findStep(chain, "verifier_subsystem_recheck");
    const durationMs = (recheckStep ?? step).duration_ms;
    if (!v?.valid) {
      return { status: "rejected", durationMs, detail: v?.reason ?? "The AI's reasoning failed verification against the evidence." };
    }
    const checks = v.checks_passed.map((c) => VERIFIER_CHECK_LABELS[c] ?? c).join("  ·  ");
    return {
      status: "passed", durationMs,
      detail: checks || "All verification checks passed.",
      loop: d.trace.feedback_loop_triggered,
    };
  }

  if (key === "deterministic_controller") {
    if (!step) return { status: "waiting", durationMs: null, detail: "Standing by." };
    const headline = d.controller_state === "AUTO_OPTIMIZE" ? "Controller approved automation."
      : d.controller_state === "CRITICAL_HALT" ? "Controller halted automation — human approval required."
      : "Controller could not confirm it is safe to automate.";
    return { status: statusOf(step), durationMs: step.duration_ms, detail: headline };
  }

  // key === "audit" — not itself a decision_chain step; every run is recorded
  // to the audit log as it happens, so once a decision exists this stage
  // reflects that logging really did occur.
  return {
    status: "passed",
    durationMs: null,
    detail: `Logged ${auditCount} audit event${auditCount === 1 ? "" : "s"} for this run.`,
  };
}

function Stage({ view, isLast }: { view: StageView; isLast: boolean }) {
  return (
    <div className={`lrp-stage lrp-${view.status}`}>
      <div className="lrp-marker">
        <span className={`lrp-dot lrp-dot-${view.status}`} />
        {!isLast && <span className="lrp-connector-line" />}
      </div>
      <div className="lrp-body">
        <div className="lrp-top">
          <span className="lrp-name">
            {view.label}
            {view.loop && (
              <span className="badge-info loop-badge" title="Verifier rejected the first pass and fed its reason back to the Risk Assessment Engine for reassessment">
                <RefreshIcon size={11} /> fed back &amp; revised
              </span>
            )}
          </span>
          <span className="lrp-right">
            {view.durationMs != null && <span className="lrp-time font-mono">{Math.round(view.durationMs)} ms</span>}
            <span className={`lrp-badge lrp-badge-${view.status}`}>{STATUS_LABEL[view.status]}</span>
          </span>
        </div>
        <div className="lrp-detail">{view.detail}</div>
      </div>
    </div>
  );
}

const STEP_MS = 260;
const RUN_MS = 170;

export function LiveRuntimePipeline() {
  const { decision, audit } = useFleet();
  const [revealed, setRevealed] = useState(0);
  const [runningIdx, setRunningIdx] = useState(-1);
  const lastRunId = useRef<string | null>(null);

  useEffect(() => {
    if (decision && decision.run_id !== lastRunId.current) {
      lastRunId.current = decision.run_id;
      setRevealed(0);
      setRunningIdx(-1);
      const timers: ReturnType<typeof setTimeout>[] = [];
      STAGE_ORDER.forEach((_, i) => {
        timers.push(setTimeout(() => setRunningIdx(i), i * STEP_MS));
        timers.push(setTimeout(() => {
          setRevealed(i + 1);
          setRunningIdx((cur) => (cur === i ? -1 : cur));
        }, i * STEP_MS + RUN_MS));
      });
      return () => timers.forEach(clearTimeout);
    }
    // Keyed on run_id only — FleetDataContext polls and hands back a fresh
    // object for the SAME run every ~1.5s, which would otherwise restart the
    // choreography mid-animation via this effect's cleanup.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [decision?.run_id]);

  const auditCount = decision ? audit.filter((r) => r.run_id === decision.run_id).length : 0;

  const stages: StageView[] = STAGE_ORDER.map((key, i) => {
    const label = STAGE_TITLES[key];
    if (!decision) return { key, label, status: "waiting", durationMs: null, detail: "Standing by." };
    const finalized = i < revealed;
    const running = i === runningIdx && !finalized;
    if (!finalized && !running) return { key, label, status: "waiting", durationMs: null, detail: "Standing by." };
    if (running) return { key, label, status: "running", durationMs: null, detail: "Executing…" };
    const built = buildStage(key, decision, auditCount);
    return { key, label, status: built.status, durationMs: built.durationMs, detail: built.detail, loop: built.loop };
  });

  return (
    <div className="lrp-card">
      <div className="lrp-header">
        <div className="mc-live-badge"><span className="mc-live-dot" />LIVE RUNTIME PIPELINE</div>
        <span className="lrp-subtitle">Two isolated agents → verified evidence → LLM reasoning → deterministic decision</span>
      </div>
      <div className="lrp-stages">
        {stages.map((s, i) => (
          <Stage key={s.key} view={s} isLast={i === stages.length - 1} />
        ))}
      </div>
    </div>
  );
}
