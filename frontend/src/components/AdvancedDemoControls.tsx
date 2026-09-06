// Fault injection is for the operator driving the demo, not for the judge's
// story — it's tucked behind a collapsed, low-emphasis toggle so it never
// competes visually with the Shipment -> Pipeline -> Timeline -> Evidence ->
// Decision narrative above it.
import { useState } from "react";
import { useFleet } from "../FleetDataContext";
import { ChevronDownIcon } from "../icons";

export function AdvancedDemoControls() {
  const [open, setOpen] = useState(false);
  const {
    sensorDrift, tripCircuitBreaker, corruptLlm, killAgent, staleSignal, runProbe,
    triggerVerifierFeedback, triggerExhaustRetries,
  } = useFleet();

  return (
    <div className="advanced-controls">
      <button type="button" className="advanced-controls-toggle" onClick={() => setOpen((o) => !o)}>
        <ChevronDownIcon size={13} className={open ? "advanced-controls-chevron open" : "advanced-controls-chevron"} />
        Advanced Demo Controls
      </button>
      {open && (
        <div className="failure-injection-bar">
          <span className="injection-label">⚡ LIVE FAILURE INJECTION & SIMULATION:</span>
          <button className="btn-inject" title="Simulate Sensor Drift" onClick={() => sensorDrift(14.5)}>
            🌡️ Sensor Drift (+14.5°C)
          </button>
          <button className="btn-inject" title="Trip LLM Circuit Breaker" onClick={tripCircuitBreaker}>
            ⚡ Trip Circuit Breaker
          </button>
          <button className="btn-inject" title="Inject Malformed LLM Output" onClick={corruptLlm}>
            💥 Corrupt LLM Payload
          </button>
          <button className="btn-inject" title="Verifier Rejects Once, Feeds Back to Risk Assessment Engine" onClick={triggerVerifierFeedback}>
            ↺ Verifier Feedback Loop
          </button>
          <button className="btn-inject" title="Exhaust All Retries — Fails Safely to INSUFFICIENT_DATA" onClick={triggerExhaustRetries}>
            ⏱️ Exhaust Retries (Safe Failure)
          </button>
          <button className="btn-inject" title="Kill Truck Sensor Agent A" onClick={() => killAgent("agent_a", true)}>
            🔌 Kill Agent A
          </button>
          <button className="btn-inject" title="Backdate Signal to Stale" onClick={() => staleSignal("cargo_temperature")}>
            ⏱️ Stale Signal
          </button>
          <button className="btn-inject" title="Run Red-Team Security Probe" onClick={runProbe}>
            🛡️ Red-Team Probe
          </button>
        </div>
      )}
    </div>
  );
}
