// Mission Control Dashboard — a single story told top to bottom: what was
// evaluated, what the harness is doing right now, why the decision was
// trusted, and what the final decision was. Nothing here should compete with
// that flow (see AdvancedDemoControls, tucked away at the bottom).
import { ShipmentEvaluationForm } from "../components/ShipmentEvaluationForm";
import { RunSummaryCard } from "../components/RunSummaryCard";
import { LiveRuntimePipeline } from "../components/LiveRuntimePipeline";
import { TimelineView } from "../components/TimelineView";
import { TrustedEvidenceCard } from "../components/ProvenanceCard";
import { FinalDecisionCard } from "../components/FinalDecisionCard";
import { HumanApprovalCard } from "../components/HumanApprovalCard";
import { AdvancedDemoControls } from "../components/AdvancedDemoControls";

export default function Dashboard() {
  return (
    <div className="page">
      <ShipmentEvaluationForm />
      <RunSummaryCard />
      <LiveRuntimePipeline />
      <TimelineView />
      <TrustedEvidenceCard />
      <FinalDecisionCard />
      <HumanApprovalCard />
      <AdvancedDemoControls />
    </div>
  );
}
