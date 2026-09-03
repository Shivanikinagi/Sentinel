import { useFleet } from "../FleetDataContext";
import { ControllerBanner, TraceView } from "../components";

const LAYERS = [
  { name: "Intelligence", module: "agents.py · critic.py", detail: "Agents isolated by code; Critic sees only structured evidence" },
  { name: "Evidence", module: "gate.py", detail: "Freshness + provenance + completeness; stale/invalid excluded" },
  { name: "Policy", module: "policy.py", detail: "Deterministic cold-chain thresholds (OPA seam)" },
  { name: "Decision", module: "controller.py · confidence.py", detail: "3-state machine; confidence computed in code, never by the LLM" },
  { name: "Authority", module: "actions.py", detail: "Action Gateway with human-in-the-loop approval" },
];

export default function HarnessPipeline() {
  const { decision, technical } = useFleet();

  return (
    <div className="page">
      <ControllerBanner d={decision} technical={technical} />
      <TraceView d={decision} technical={technical} />

      <div className="panel">
        <h2>Architecture Layers{technical && <span className="tech-caption"> · never collapsed into one LLM call</span>}</h2>
        <div className="layer-list">
          {LAYERS.map((l) => (
            <div className="layer-row" key={l.name}>
              <div className="layer-name">{l.name}</div>
              <div className="layer-body">
                <div className="layer-detail">{l.detail}</div>
                {technical && <div className="tech-caption">{l.module}</div>}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
