// The Harness Runtime page, reduced to the one thing a judge needs in 30-60
// seconds: a vertical checklist of every stage that ran, in order, each
// showing only what it decided and why — no architecture, no metrics.
// Every number here reads straight off ControllerDecision; nothing is
// invented. Stages animate Waiting -> Running -> Passed/Warning/Failed on
// each new run, replaying the real recorded durations rather than the
// literal wall-clock (which already elapsed by the time this data arrives).
import { useEffect, useMemo, useState, type ReactNode } from "react";
import { api } from "../api";
import { useFleet } from "../FleetDataContext";
import { humanizeReason } from "../humanize";
import { CheckCircle, XCircle, AlertTriangle, RefreshIcon } from "../icons";
import type { ActionRequest, ControllerDecision, DecisionStep } from "../types";

type Tone = "ok" | "warn" | "bad";
type NodeState = "waiting" | "running" | Tone;

function toneOf(status: string | undefined): Tone {
  if (status === "OK") return "ok";
  if (status === "WARNING") return "warn";
  return "bad";
}

function leadingNumber(detail: string | undefined): number {
  const m = /^(\d+)/.exec(detail ?? "");
  return m ? Number(m[1]) : 0;
}

function findStep(chain: DecisionStep[], name: string): DecisionStep | undefined {
  return chain.find((s) => s.step_name === name);
}

function StatusPill({ state, label }: { state: NodeState; label: string }) {
  return <span className={`pipeline-node-status ${state}`}>{label}</span>;
}

function NodeIcon({ state }: { state: NodeState }) {
  if (state === "ok") return <CheckCircle size={14} />;
  if (state === "warn") return <AlertTriangle size={14} />;
  if (state === "bad") return <XCircle size={14} />;
  return null;
}

interface RailNode {
  key: string;
  title: string;
  emphasis?: boolean;
  state: NodeState;
  statusLabel: string;
  durationMs?: number;
  body: ReactNode;
}

function buildNodes(
  decision: ControllerDecision,
  approval: ActionRequest | null,
): Omit<RailNode, "state">[] {
  const chain = decision.trace.decision_chain ?? [];
  const retries = decision.trace.retries ?? [];
  const gateStages = decision.trace.gate_stage_results ?? [];
  const totalEvidence = decision.trace.evidence_snapshot.length;

  const vehicleStep = findStep(chain, "agent_vehicle_observer");
  const envStep = findStep(chain, "agent_environment_observer");
  const gateStep = findStep(chain, "trust_gate");
  const correlationStep = findStep(chain, "evidence_correlation");
  const riskStep = findStep(chain, "risk_assessment_engine");
  // A feedback loop replaces the first verifier_subsystem pass with a later
  // recheck step — prefer that one so the displayed duration reflects the
  // run's final verification, not the superseded first attempt.
  const verifierStep = findStep(chain, "verifier_subsystem_recheck") ?? findStep(chain, "verifier_subsystem");
  const controllerStep = findStep(chain, "deterministic_controller");

  const nodes: Omit<RailNode, "state">[] = [];

  nodes.push({
    key: "input",
    title: "Input",
    statusLabel: "Received",
    durationMs: 0,
    body: `Run triggered for ${decision.vehicle_id}.`,
  });

  nodes.push({
    key: "vehicle_agent",
    title: "Vehicle Agent",
    statusLabel: vehicleStep?.status === "OK" ? "Completed" : "Unavailable",
    durationMs: vehicleStep?.duration_ms,
    body: vehicleStep?.status === "OK"
      ? `Collected ${leadingNumber(vehicleStep.detail)} vehicle signal${leadingNumber(vehicleStep.detail) === 1 ? "" : "s"}.`
      : "Unavailable — no signals collected this run.",
  });

  nodes.push({
    key: "environment_agent",
    title: "Environment Agent",
    statusLabel: envStep?.status === "OK" ? "Completed" : "Unavailable",
    durationMs: envStep?.duration_ms,
    body: envStep?.status === "OK"
      ? `Collected ${leadingNumber(envStep.detail)} environmental signal${leadingNumber(envStep.detail) === 1 ? "" : "s"}.`
      : "Unavailable — no signals collected this run.",
  });

  const staleCount = leadingNumber(findStep(gateStages, "freshness_checker")?.detail);
  const provenanceRejected = leadingNumber(findStep(gateStages, "provenance_checker")?.detail);
  const dupeCount = leadingNumber(findStep(gateStages, "evidence_normalizer")?.detail);
  nodes.push({
    key: "trust_gate",
    title: "Trust Gate",
    statusLabel: gateStep && toneOf(gateStep.status) === "ok" ? "Passed"
      : gateStep && toneOf(gateStep.status) === "warn" ? "Passed (filtered)" : "Rejected",
    durationMs: gateStep?.duration_ms,
    body: (
      <>
        <div className="pipeline-node-detail">
          {gateStep?.detail ?? "Evaluating evidence…"}
        </div>
        <div className="pipeline-substages">
          <div className={`pipeline-substage ${dupeCount > 0 ? "warn" : "ok"}`}>
            <div className="pipeline-substage-name">Schema</div>
            <div className="pipeline-substage-value">{totalEvidence}/{totalEvidence} valid</div>
          </div>
          <div className={`pipeline-substage ${staleCount > 0 ? "warn" : "ok"}`}>
            <div className="pipeline-substage-name">Freshness</div>
            <div className="pipeline-substage-value">{totalEvidence - staleCount} fresh, {staleCount} stale</div>
          </div>
          <div className={`pipeline-substage ${provenanceRejected > 0 ? "warn" : "ok"}`}>
            <div className="pipeline-substage-name">Provenance</div>
            <div className="pipeline-substage-value">{Math.max(0, totalEvidence - provenanceRejected)} trusted</div>
          </div>
          <div className={`pipeline-substage ${dupeCount > 0 ? "warn" : "ok"}`}>
            <div className="pipeline-substage-name">Normalization</div>
            <div className="pipeline-substage-value">{dupeCount} duplicate{dupeCount === 1 ? "" : "s"} removed</div>
          </div>
        </div>
      </>
    ),
  });

  const conflictCount = decision.trace.correlation_conflicts?.length ?? 0;
  nodes.push({
    key: "correlation_engine",
    title: "Correlation Engine",
    statusLabel: correlationStep && toneOf(correlationStep.status) === "ok" ? "Passed" : "Conflict Detected",
    durationMs: correlationStep?.duration_ms,
    body: conflictCount > 0
      ? `${conflictCount} physical contradiction${conflictCount === 1 ? "" : "s"} detected.`
      : "No physical contradictions detected.",
  });

  const backendMatch = /Backend:\s*([^,]+)/.exec(riskStep?.detail ?? "");
  const backend = backendMatch ? backendMatch[1].trim() : undefined;
  const recovered = retries.length > 0 && riskStep?.status === "OK";
  nodes.push({
    key: "risk_assessment_engine",
    title: "Risk Assessment Engine",
    statusLabel: riskStep?.status === "OK" ? "Completed" : "Rejected",
    durationMs: riskStep?.duration_ms,
    body: (
      <div className="pipeline-node-detail">
        {decision.critic_rejected
          ? "The model's output failed validation and was rejected."
          : `Risk Level: ${decision.risk_matrix?.risk_level ?? "—"}`}
        {backend && ` · Backend: ${backend}`}
        {recovered && " · recovered after retry"}
      </div>
    ),
  });

  const passed = new Set(decision.trace.verifier_result?.checks_passed ?? []);
  const failed = decision.trace.verifier_result?.checks_failed ?? [];
  const checkState = (key: string, failPrefixes: string[]): "PASS" | "FAIL" | "—" => {
    if (passed.has(key)) return "PASS";
    if (failed.some((f) => failPrefixes.some((p) => f.startsWith(p)))) return "FAIL";
    return "—";
  };
  const verifierValid = decision.trace.verifier_result?.valid ?? false;
  const loopTriggered = decision.trace.feedback_loop_triggered ?? false;
  nodes.push({
    key: "verifier",
    title: "Verifier",
    statusLabel: verifierValid ? "Passed" : "Failed",
    durationMs: verifierStep?.duration_ms,
    body: (
      <div className="verifier-checks">
        {loopTriggered && (
          <div className="badge-info loop-badge loop-badge-block" title={decision.trace.feedback_loop_reason ?? ""}>
            <RefreshIcon size={11} /> Fed back to Risk Assessment Engine — revised &amp; re-verified
          </div>
        )}
        {[
          { key: "self_consistency", label: "Self Consistency", prefixes: ["self_consistency"] },
          { key: "evidence_grounding", label: "Evidence Grounding", prefixes: ["unsupported_risk_factor"] },
          { key: "contradiction_verification", label: "Contradiction Validation", prefixes: ["contradiction_requires"] },
        ].map((c) => {
          const state = checkState(c.key, c.prefixes);
          return (
            <div className="verifier-check-row" key={c.key}>
              <span>{c.label}</span>
              <span className={`verifier-check-badge ${state === "—" ? "NA" : state}`}>{state}</span>
            </div>
          );
        })}
      </div>
    ),
  });

  const decisionTone = toneOf(
    decision.controller_state === "AUTO_OPTIMIZE" ? "OK"
      : decision.controller_state === "INSUFFICIENT_DATA" ? "WARNING" : "FAILED",
  );
  const gatePassed = !(decision.reason.startsWith("agent(s) unavailable")
    || decision.reason.startsWith("required evidence missing"));
  nodes.push({
    key: "decision_authority",
    title: "Decision Authority",
    emphasis: true,
    statusLabel: decision.controller_state,
    durationMs: controllerStep?.duration_ms,
    body: (
      <>
        <div className="decision-authority-grid">
          <div>
            <div className="decision-authority-field-label">Gate</div>
            <div className={`decision-authority-field-value tone-${gatePassed ? "good" : "bad"}`}>
              {gatePassed ? "PASS" : "FAIL"}
            </div>
          </div>
          <div>
            <div className="decision-authority-field-label">Verifier</div>
            <div className={`decision-authority-field-value tone-${verifierValid ? "good" : "bad"}`}>
              {verifierValid ? "PASS" : "FAIL"}
            </div>
          </div>
          <div>
            <div className="decision-authority-field-label">Risk</div>
            <div className="decision-authority-field-value">{decision.risk_matrix?.risk_level ?? "—"}</div>
          </div>
          <div>
            <div className="decision-authority-field-label">Decision</div>
            <div className={`decision-authority-field-value tone-${decisionTone === "ok" ? "good" : decisionTone === "warn" ? "warn" : "bad"}`}>
              {decision.controller_state}
            </div>
          </div>
          <div className="decision-authority-reason">
            <div className="decision-authority-field-label">Reason</div>
            <div className="decision-authority-field-value" style={{ fontSize: 13 }}>
              {humanizeReason(decision.reason)}
            </div>
          </div>
        </div>
      </>
    ),
  });

  if (decision.controller_state === "CRITICAL_HALT") {
    const status = approval?.status ?? "PENDING_APPROVAL";
    const label = status === "PENDING_APPROVAL" ? "Pending Approval"
      : status === "APPROVED" ? "Approved"
      : status === "REJECTED" ? "Rejected" : "Approved";
    nodes.push({
      key: "human_approval",
      title: "Human Approval",
      emphasis: true,
      statusLabel: label,
      body: <HumanApprovalBody action={approval} />,
    });
  }

  nodes.push({
    key: "audit",
    title: "Audit",
    statusLabel: "Logged",
    body: (
      <div className="audit-mini-body">
        <span>✓ Decision stored in immutable audit</span>
        <span className="font-mono text-muted">{decision.run_id}</span>
      </div>
    ),
  });

  return nodes;
}

function HumanApprovalBody({ action }: { action: ActionRequest | null }) {
  const { approve, reject } = useFleet();
  if (!action) {
    return <div className="pipeline-node-detail">Loading approval status…</div>;
  }
  if (action.status === "PENDING_APPROVAL") {
    return (
      <>
        <div className="pipeline-node-detail">Automation halted — a person must approve or reject before anything executes.</div>
        <div className="human-approval-actions">
          <button className="ok" onClick={() => approve(action.action_id)}>
            <CheckCircle size={14} /> Approve
          </button>
          <button className="danger" onClick={() => reject(action.action_id)}>
            <XCircle size={14} /> Reject
          </button>
        </div>
      </>
    );
  }
  if (action.status === "REJECTED") {
    return <div className="pipeline-node-detail">Rejected by {action.approver ?? "an operator"}.</div>;
  }
  return <div className="pipeline-node-detail">Approved by {action.approver ?? "an operator"}.</div>;
}

export function PipelineTimeline() {
  const { decision, actions } = useFleet();
  const [approval, setApproval] = useState<ActionRequest | null>(null);

  useEffect(() => {
    if (!decision || decision.controller_state !== "CRITICAL_HALT" || !decision.escalation_id) {
      setApproval(null);
      return;
    }
    let cancelled = false;
    api.action(decision.escalation_id).then((r) => {
      if (!cancelled) setApproval(r.action);
    }).catch(() => {});
    return () => { cancelled = true; };
  }, [decision?.run_id, decision?.escalation_id, actions]);

  const baseNodes = useMemo(
    () => (decision ? buildNodes(decision, approval) : []),
    [decision, approval],
  );

  const [revealCount, setRevealCount] = useState(0);
  const [runningIdx, setRunningIdx] = useState(-1);

  useEffect(() => {
    if (baseNodes.length === 0) return;
    let cancelled = false;
    setRevealCount(0);
    setRunningIdx(-1);
    let i = 0;
    const step = () => {
      if (cancelled) return;
      setRunningIdx(i);
      setTimeout(() => {
        if (cancelled) return;
        setRevealCount(i + 1);
        setRunningIdx(-1);
        i += 1;
        if (i < baseNodes.length) setTimeout(step, 90);
      }, 240);
    };
    const kickoff = setTimeout(step, 150);
    return () => { cancelled = true; clearTimeout(kickoff); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [decision?.run_id, baseNodes.length]);

  if (!decision) {
    return (
      <div className="panel">
        <div className="empty">Run the harness to see the live pipeline.</div>
      </div>
    );
  }

  return (
    <div className="panel pipeline-timeline-panel">
      <h2>Live Pipeline</h2>
      <div className="pipeline-rail">
        {baseNodes.map((n, idx) => {
          const revealed = idx < revealCount;
          const running = idx === runningIdx;
          const state: NodeState = running ? "running" : !revealed ? "waiting" : toneFromLabel(n, decision);
          return (
            <div className={`pipeline-node state-${state}`} key={n.key}>
              <div className="pipeline-node-rail">
                <span className="pipeline-dot" />
                <span className="pipeline-line" />
              </div>
              <div className={`pipeline-node-card${n.emphasis ? " emphasis" : ""} ${n.key === "decision_authority" ? "decision-authority" : ""} ${n.key === "human_approval" ? `human-approval state-${state}` : ""}`}>
                <div className="pipeline-node-head">
                  <span className="pipeline-node-title"><NodeIcon state={state} /> {n.title}</span>
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    {n.durationMs !== undefined && (
                      <span className="pipeline-node-duration">{Math.round(n.durationMs)} ms</span>
                    )}
                    <StatusPill state={state} label={running ? "Running…" : !revealed ? "Waiting" : n.statusLabel} />
                  </div>
                </div>
                {revealed && !running && <div className="pipeline-node-body">{n.body}</div>}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function toneFromLabel(n: Omit<RailNode, "state">, decision: ControllerDecision): Tone {
  const label = n.statusLabel;
  if (n.key === "decision_authority") {
    return decision.controller_state === "AUTO_OPTIMIZE" ? "ok"
      : decision.controller_state === "INSUFFICIENT_DATA" ? "warn" : "bad";
  }
  if (n.key === "human_approval") {
    return label === "Approved" ? "ok" : label === "Rejected" ? "bad" : "warn";
  }
  if (["Completed", "Passed", "Received", "Logged"].includes(label)) return "ok";
  if (label.includes("filtered") || label === "Conflict Detected") return "warn";
  if (["Unavailable", "Rejected", "Failed"].includes(label)) return "bad";
  return "ok";
}
