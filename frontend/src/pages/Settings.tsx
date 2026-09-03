import { useFleet } from "../FleetDataContext";

export default function Settings() {
  const { backend, technical, setMode, world } = useFleet();

  return (
    <div className="page">
      <div className="panel">
        <h2>View Mode</h2>
        <p className="panel-sub">
          Simple mode shows plain-English labels for operators. Technical mode adds the
          underlying harness vocabulary (agent names, RiskMatrix, gate notes) as captions.
        </p>
        <div className="mode-toggle" role="tablist" aria-label="View mode" style={{ marginTop: 10 }}>
          <button role="tab" aria-selected={!technical} className={!technical ? "active" : ""} onClick={() => setMode(false)}>
            Simple
          </button>
          <button role="tab" aria-selected={technical} className={technical ? "active" : ""} onClick={() => setMode(true)}>
            Technical
          </button>
        </div>
      </div>

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
