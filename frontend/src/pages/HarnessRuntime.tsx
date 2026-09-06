import { RunSummaryCard } from "../components/RunSummaryCard";
import { PipelineTimeline } from "../components/PipelineTimeline";

export default function HarnessRuntime() {
  return (
    <div className="page">
      <RunSummaryCard />
      <PipelineTimeline />
    </div>
  );
}
