import { useFleet } from "../FleetDataContext";
import { ControllerBanner, TraceView } from "../components";
import { PipelineVisualizer } from "../components/PipelineVisualizer";
import { ExecutionTimeCard } from "../components/ExecutionTimeCard";
import { TokenUsageCard } from "../components/TokenUsageCard";
import { FeedbackLoopDiagram } from "../components/FeedbackLoopDiagram";
import { SafetyGuardrailCard } from "../components/SafetyGuardrailCard";
import { PolicyPackCard } from "../components/PolicyPackCard";

// Same 7 stages every run actually passes through, named the way a judge
// reads them rather than the internal module name — the internal name is
// still there, just secondary (technical caption).
const LAYERS = [
  { name: "Agents", module: "agents.py", detail: "Two isolated observers, no shared code path" },
  { name: "Evidence", module: "schemas.py · run_state.py", detail: "Raw signals, immutable, sourced" },
  { name: "Trust", module: "gate.py", detail: "Fresh, sourced, complete — or excluded" },
  { name: "Reasoning", module: "critic.py", detail: "The only LLM in the path — advisory only" },
  { name: "Verification", module: "verifier.py", detail: "Checks the LLM against the evidence it saw" },
  { name: "Policy", module: "policy_packs.py · controller.py", detail: "Swappable domain rules, deterministic decision" },
  { name: "Authority", module: "actions.py", detail: "Human approves every halt" },
];

export default function HarnessPipeline() {
  const { decision, technical } = useFleet();

  return (
    <div className="page">
      <PipelineVisualizer />
      <ControllerBanner d={decision} technical={technical} />
      <SafetyGuardrailCard />
      <FeedbackLoopDiagram />

      <div className="dash-grid">
        <ExecutionTimeCard />
        <TokenUsageCard />
      </div>

      <PolicyPackCard />
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
