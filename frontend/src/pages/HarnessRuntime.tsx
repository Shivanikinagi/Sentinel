import { HarnessRuntimeDiagram } from "../components/HarnessRuntimeDiagram";
import { SupervisorConsole } from "../components/SupervisorConsole";
import { HarnessMetricsPanel } from "../components/HarnessMetricsPanel";
import { PolicyPackCard } from "../components/PolicyPackCard";
import { ConfidenceBreakdownCard } from "../components/ConfidenceBreakdownCard";
import { VehicleTrendCard } from "../components/VehicleTrendCard";
import { IncidentMemoryPanel } from "../components/IncidentMemoryPanel";
import { IsolationDemoCard } from "../components/IsolationDemoCard";
import { WorldStateCard } from "../components/WorldStateCard";
import { TimelineView } from "../components/TimelineView";
import { DecisionCertificate } from "../components/DecisionCertificate";

export default function HarnessRuntime() {
  return (
    <div className="page">
      <HarnessRuntimeDiagram />
      <SupervisorConsole />
      <HarnessMetricsPanel />
      <PolicyPackCard />

      <div className="dash-grid">
        <ConfidenceBreakdownCard />
        <VehicleTrendCard />
      </div>

      <div className="dash-grid">
        <WorldStateCard />
        <IsolationDemoCard />
      </div>

      <TimelineView />
      <DecisionCertificate />
      <IncidentMemoryPanel />
    </div>
  );
}
