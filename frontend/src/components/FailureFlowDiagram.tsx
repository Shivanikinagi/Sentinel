// Turns "break something on purpose" from two buttons into a visible chain
// reaction. Every node's active/inactive state is read off the real World
// switches + the latest ControllerDecision — nothing here is scripted; a
// scenario that doesn't actually trip a stage (e.g. a healthy run) just shows
// that stage as not triggered.
import { useEffect, useState } from "react";
import { useFleet } from "../FleetDataContext";
import { CheckCircle, XCircle, ZapIcon } from "../icons";

interface FlowNode {
  key: string;
  title: string;
  triggered: boolean;
  detail: string;
}

export function FailureFlowDiagram() {
  const { decision, world } = useFleet();
  const sw = world?.switches;

  const failureLabel = sw?.agent_b_disabled ? "Route sensors disconnected"
    : sw?.corrupt_critic ? "AI output corrupted"
    : sw?.force_stale_signal ? "Telemetry forced stale"
    : sw?.agent_a_disabled ? "Truck sensors disconnected"
    : null;

  const excludedCount = decision?.trace.excluded_evidence_ids.length ?? 0;
  const agentsDown = decision?.trace.agents_unavailable.length ?? 0;
  const verifierFailed = decision ? !(decision.trace.verifier_result?.valid ?? true) : false;
  const riskUp = decision?.risk_matrix?.risk_level === "HIGH" || decision?.risk_matrix?.risk_level === "MEDIUM" || !!decision?.critic_rejected;
  const needsApproval = decision?.controller_state === "CRITICAL_HALT";

  const nodes: FlowNode[] = [
    {
      key: "failure",
      title: "Failure Injected",
      triggered: !!failureLabel,
      detail: failureLabel ?? "No fault armed",
    },
    {
      key: "gate",
      title: "Trust Gate",
      triggered: excludedCount > 0 || agentsDown > 0,
      detail: agentsDown > 0 ? `${agentsDown} agent(s) unavailable` : excludedCount > 0 ? `${excludedCount} signal(s) flagged` : "All signals passed",
    },
    {
      key: "evidence",
      title: "Evidence Removed",
      triggered: excludedCount > 0,
      detail: excludedCount > 0 ? `${excludedCount} reading(s) excluded` : "Nothing excluded",
    },
    {
      key: "verifier",
      title: "Verifier Failed",
      triggered: verifierFailed || !!decision?.critic_rejected,
      detail: decision?.critic_rejected ? "AI output rejected by schema" : verifierFailed ? "Contradicted the evidence" : "Verifier passed",
    },
    {
      key: "risk",
      title: "Risk Increased",
      triggered: riskUp,
      detail: decision?.risk_matrix ? `Risk level: ${decision.risk_matrix.risk_level}` : "No elevated risk",
    },
    {
      key: "approval",
      title: "Human Approval Required",
      triggered: needsApproval,
      detail: needsApproval ? "Automation halted pending sign-off" : "No approval needed",
    },
  ];

  const [revealCount, setRevealCount] = useState(nodes.length);
  useEffect(() => {
    setRevealCount(0);
    let i = 0;
    const step = () => {
      i += 1;
      setRevealCount(i);
      if (i < nodes.length) timer = setTimeout(step, 180);
    };
    let timer = setTimeout(step, 120);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [decision?.run_id, sw?.agent_a_disabled, sw?.agent_b_disabled, sw?.corrupt_critic, sw?.force_stale_signal]);

  return (
    <div className="panel">
      <h2><ZapIcon size={13} /> Failure Injection Flow</h2>
      <div className="failure-flow">
        {nodes.map((n, i) => {
          const revealed = i < revealCount;
          return (
            <div className={`failure-flow-node ${n.triggered ? "triggered" : "idle"} ${revealed ? "revealed" : ""}`} key={n.key}>
              <div className="failure-flow-icon">
                {n.triggered ? <XCircle size={16} /> : <CheckCircle size={16} />}
              </div>
              <div className="failure-flow-body">
                <div className="failure-flow-title">{n.title}</div>
                <div className="failure-flow-detail">{n.detail}</div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
