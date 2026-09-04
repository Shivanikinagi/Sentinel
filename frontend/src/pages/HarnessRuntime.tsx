import { HarnessRuntimeDiagram } from "../components/HarnessRuntimeDiagram";
import { HarnessMetricsPanel } from "../components/HarnessMetricsPanel";
import { PolicyPackCard } from "../components/PolicyPackCard";
import { ConfidenceBreakdownCard } from "../components/ConfidenceBreakdownCard";
import { VehicleTrendCard } from "../components/VehicleTrendCard";
import { TimelineView } from "../components/TimelineView";

export default function HarnessRuntime() {
  return (
    <div className="page">
      <HarnessRuntimeDiagram />
      <HarnessMetricsPanel />
      <PolicyPackCard />

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "24px" }}>
        <ConfidenceBreakdownCard />
        <VehicleTrendCard />
      </div>

      <TimelineView />
    </div>
  );
}
