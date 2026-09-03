import { HashRouter, Route, Routes } from "react-router-dom";
import { FleetDataProvider } from "./FleetDataContext";
import { AppLayout } from "./layout/AppLayout";
import Dashboard from "./pages/Dashboard";
import VehicleDetails from "./pages/VehicleDetails";
import HarnessPipeline from "./pages/HarnessPipeline";
import SimulationLab from "./pages/SimulationLab";
import AuditLogs from "./pages/AuditLogs";
import Analytics from "./pages/Analytics";
import Settings from "./pages/Settings";

export default function App() {
  return (
    <FleetDataProvider>
      <HashRouter>
        <Routes>
          <Route element={<AppLayout />}>
            <Route path="/" element={<Dashboard />} />
            <Route path="/vehicle" element={<VehicleDetails />} />
            <Route path="/pipeline" element={<HarnessPipeline />} />
            <Route path="/simulation" element={<SimulationLab />} />
            <Route path="/audit" element={<AuditLogs />} />
            <Route path="/analytics" element={<Analytics />} />
            <Route path="/settings" element={<Settings />} />
          </Route>
        </Routes>
      </HashRouter>
    </FleetDataProvider>
  );
}
