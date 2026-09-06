import { useFleet } from "../FleetDataContext";

export default function Settings() {
  const { backend, world } = useFleet();

  return (
    <div className="page">
      <div className="panel">
        <h2>Environment</h2>
        <div className="settings-rows">
          <div className="settings-row"><span>AI backend</span><span className="badge">{backend}</span></div>
          <div className="settings-row"><span>Scenario</span><span className="badge">{world?.scenario ?? "—"}</span></div>
          <div className="settings-row"><span>API base</span><span className="badge">{import.meta.env.VITE_API_BASE ?? "http://localhost:8000"}</span></div>
        </div>
      </div>
    </div>
  );
}
