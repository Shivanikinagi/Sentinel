import { useFleet } from "../FleetDataContext";
import { ControllerBanner, SecurityProbe } from "../components";
import { PlayIcon, RefreshIcon, ZapIcon } from "../icons";

export default function SimulationLab() {
  const {
    decision, world, technical, busy, runNow, setScenario, killAgent, corruptLlm,
    staleSignal, reset, probe, runProbe, triggerTransientError,
  } = useFleet();

  const sw = world?.switches;
  const isCompound = world?.scenario === "compound_risk";

  return (
    <div className="page">
      <div className="panel">
        <h2>Drive the Scenario</h2>
        <div className="control-groups">
          <div className="control-group">
            <div className="control-label">Run a check</div>
            <div className="controls">
              <button className="primary" disabled={busy} onClick={runNow}>
                <PlayIcon size={13} /> Run check
              </button>
              <button disabled={busy || !isCompound} onClick={() => setScenario("healthy")}>
                Normal conditions
              </button>
              <button className="warn" disabled={busy || !!isCompound} onClick={() => setScenario("compound_risk")}>
                Simulate risky situation
              </button>
              <button disabled={busy} onClick={reset}>
                <RefreshIcon size={13} /> Reset
              </button>
            </div>
          </div>

          <div className="control-group">
            <div className="control-label">Break something on purpose</div>
            <div className="controls">
              <button
                className="danger" disabled={busy}
                onClick={() => killAgent("agent_b", !sw?.agent_b_disabled)}
              >
                {sw?.agent_b_disabled ? "Reconnect route sensors" : "Disconnect route sensors"}
              </button>
              <button className="warn" disabled={busy} onClick={corruptLlm}>
                <ZapIcon size={12} /> Simulate AI glitch
              </button>
              <button
                className="warn" disabled={busy}
                onClick={() => staleSignal(sw?.force_stale_signal ? null : "cargo_temperature")}
              >
                {sw?.force_stale_signal ? "Clear old data" : "Simulate old data"}
              </button>
              <button className="warn" disabled={busy} onClick={triggerTransientError}>
                <ZapIcon size={12} /> Simulate network blip (Retry Engine)
              </button>
            </div>
          </div>
        </div>
      </div>

      <ControllerBanner d={decision} technical={technical} />

      <div className="dash-grid">
        <div className="panel">
          <h2>System Indicators{technical && <span className="tech-caption"> · live switches</span>}</h2>
          <div className="indicator-grid">
            <Indicator label="Truck Sensors" ok={!sw?.agent_a_disabled} />
            <Indicator label="Route Conditions" ok={!sw?.agent_b_disabled} />
            <Indicator label="AI Critic" ok={!sw?.corrupt_critic} warnLabel="glitch armed" />
            <Indicator label="Data Freshness" ok={!sw?.force_stale_signal} warnLabel="forced stale" />
            <Indicator label="Controller" ok={decision?.controller_state !== "CRITICAL_HALT"} />
            <Indicator label="Escalation" ok={!decision?.escalation_id} warnLabel="open" />
          </div>
        </div>

        <SecurityProbe result={probe} onProbe={runProbe} technical={technical} />
      </div>
    </div>
  );
}

function Indicator({ label, ok, warnLabel }: { label: string; ok: boolean; warnLabel?: string }) {
  return (
    <div className="indicator-cell">
      <span className={`dot ${ok ? "dot-good" : "dot-warn"}`} />
      <div>
        <div className="indicator-label">{label}</div>
        <div className="indicator-state">{ok ? "Nominal" : (warnLabel ?? "Degraded")}</div>
      </div>
    </div>
  );
}
