import { useFleet } from "../FleetDataContext";
import { ControllerBanner, TraceView } from "../components";
import { PipelineVisualizer } from "../components/PipelineVisualizer";

const LAYERS = [
  { name: "Intelligence", module: "agents.py · critic.py", detail: "Agents isolated by code; evidence only" },
  { name: "Evidence", module: "gate.py", detail: "Fresh, sourced, complete — or excluded" },
  { name: "Policy", module: "policy_packs.py", detail: "Swappable domain rules, not hardcoded" },
  { name: "Decision", module: "controller.py · confidence.py", detail: "3 states, confidence computed in code" },
  { name: "Authority", module: "actions.py", detail: "Human approves every halt" },
];

export default function HarnessPipeline() {
  const { decision, technical } = useFleet();

  return (
    <div className="page">
      <PipelineVisualizer />
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
