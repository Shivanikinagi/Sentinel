// Makes the Supervisor visible, not just architecturally real: a console-style
// log of what it actually did this run — launched each agent, waited, retried
// a failed Risk Assessment Engine call, completed. Built entirely from the
// existing decision_chain / retries fields, no new backend data.
import { useEffect, useState } from "react";
import { useFleet } from "../FleetDataContext";
import { stepLabel } from "../humanize";

type LineTone = "info" | "ok" | "warn" | "bad";

interface ConsoleLine {
  text: string;
  tone: LineTone;
}

function buildLines(decision: ReturnType<typeof useFleet>["decision"]): ConsoleLine[] {
  if (!decision) return [];
  const lines: ConsoleLine[] = [{ text: "Supervisor: planning execution…", tone: "info" }];

  for (const step of decision.trace.decision_chain ?? []) {
    if (step.step_name.startsWith("agent_")) {
      const label = stepLabel(step.step_name);
      lines.push({ text: `Supervisor: launching ${label}…`, tone: "info" });
      lines.push({
        text: step.status === "OK" ? `${label}: ${step.detail}` : `${label}: ${step.detail}`,
        tone: step.status === "OK" ? "ok" : "bad",
      });
    } else if (step.step_name.startsWith("retry_")) {
      lines.push({ text: `Supervisor: retrying Risk Assessment Engine — ${step.detail}`, tone: "warn" });
    } else if (step.step_name === "risk_assessment_engine") {
      const recovered = /\((\d+) attempts?\)/.exec(step.detail);
      if (recovered && Number(recovered[1]) > 1) {
        lines.push({ text: "Supervisor: Risk Assessment Engine recovered ✓", tone: "ok" });
      }
    }
  }

  lines.push({
    text: `Supervisor: run complete — ${decision.controller_state}`,
    tone: decision.controller_state === "CRITICAL_HALT" ? "bad"
      : decision.controller_state === "AUTO_OPTIMIZE" ? "ok" : "warn",
  });
  return lines;
}

export function SupervisorConsole() {
  const { decision } = useFleet();
  const lines = buildLines(decision);
  const [visible, setVisible] = useState(lines.length);

  useEffect(() => {
    const next = buildLines(decision).length;
    setVisible(0);
    let i = 0;
    const tick = () => {
      i += 1;
      setVisible(i);
      if (i < next) setTimeout(tick, 220);
    };
    if (next > 0) setTimeout(tick, 120);
  }, [decision?.run_id]);

  const retryCount = decision?.trace.retries?.length ?? 0;
  const agentSteps = (decision?.trace.decision_chain ?? []).filter((s) => s.step_name.startsWith("agent_"));
  const failedAgents = agentSteps.filter((s) => s.status === "FAILED").length;

  if (!decision) return null;

  return (
    <div className="panel">
      <h2>Supervisor Console</h2>
      <div className="supervisor-console">
        {lines.slice(0, visible).map((l, i) => (
          <div key={i} className={`console-line tone-${l.tone}`}>
            <span className="console-prompt">$</span> {l.text}
          </div>
        ))}
      </div>
      <div className="failure-counters">
        <div className="failure-counter">
          <span className="failure-counter-label">Agents Launched</span>
          <span className="failure-counter-value">{agentSteps.length}</span>
        </div>
        <div className="failure-counter">
          <span className="failure-counter-label">Agent Failures</span>
          <span className={`failure-counter-value${failedAgents ? " tone-bad" : ""}`}>{failedAgents}</span>
        </div>
        <div className="failure-counter">
          <span className="failure-counter-label">Retries</span>
          <span className={`failure-counter-value${retryCount ? " tone-warn" : ""}`}>{retryCount}</span>
        </div>
        <div className="failure-counter">
          <span className="failure-counter-label">Recovered</span>
          <span className="failure-counter-value tone-ok">{retryCount > 0 && !decision.critic_rejected ? "✓" : "—"}</span>
        </div>
      </div>
    </div>
  );
}
