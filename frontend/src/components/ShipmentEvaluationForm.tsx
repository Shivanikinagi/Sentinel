// Live Scenario Runner — the operator's entry point into the Harness Runtime.
// Replaces the old "Healthy Demo / Contradiction Demo" buttons: instead of
// launching a canned scene, the operator submits real shipment telemetry,
// which flows through POST /simulate/shipment (world truth only) and then
// POST /runs (the real, unchanged multi-agent pipeline). Presets just
// pre-fill the form with values that are known to exercise a specific,
// real controller rule — nothing about the run itself is scripted.
import { useState, type FormEvent } from "react";
import { useFleet } from "../FleetDataContext";
import { PlayIcon } from "../icons";

interface PresetDef {
  label: string;
  hint: string;
  cargoTemp: number;
  ambientTemp: number;
  cooling: boolean;
  dwellMinutes?: number;
  agentBDisabled?: boolean;
  corruptCritic?: boolean;
  staleSignal?: string | null;
}

type PresetKey =
  | "healthy" | "cooling_failure" | "sensor_contradiction"
  | "missing_sensor" | "agent_failure" | "stale_evidence";

const PRESETS: Record<PresetKey, PresetDef> = {
  healthy: {
    label: "Healthy Shipment", hint: "All signals nominal.",
    cargoTemp: 4, ambientTemp: 22, cooling: true,
  },
  cooling_failure: {
    label: "Cooling Failure", hint: "Cooling unit truly OFF, cargo genuinely rising.",
    cargoTemp: 11, ambientTemp: 25, cooling: false,
  },
  sensor_contradiction: {
    label: "Sensor Contradiction", hint: "Cooling reports ON while cargo reads hot — physically impossible.",
    cargoTemp: 11.5, ambientTemp: 41, cooling: true, dwellMinutes: 37,
  },
  missing_sensor: {
    label: "Missing Sensor", hint: "The Environment Agent stops reporting entirely.",
    cargoTemp: 4, ambientTemp: 22, cooling: true, agentBDisabled: true,
  },
  agent_failure: {
    label: "Agent Failure", hint: "The Risk Assessment Engine returns a malformed result.",
    cargoTemp: 4, ambientTemp: 22, cooling: true, corruptCritic: true,
  },
  stale_evidence: {
    label: "Stale Evidence", hint: "Cargo temperature reading is backdated past the freshness window.",
    cargoTemp: 4, ambientTemp: 22, cooling: true, staleSignal: "cargo_temperature",
  },
};

function newShipmentId(): string {
  return `SHP-${Math.random().toString(36).slice(2, 7).toUpperCase()}`;
}

export function ShipmentEvaluationForm() {
  const { evaluateShipment, busy } = useFleet();

  const [preset, setPreset] = useState<PresetKey>("healthy");
  const [shipmentId, setShipmentId] = useState(newShipmentId);
  const [vehicleId, setVehicleId] = useState("TRUCK-042");
  const [cargoTemp, setCargoTemp] = useState(PRESETS.healthy.cargoTemp);
  const [ambientTemp, setAmbientTemp] = useState(PRESETS.healthy.ambientTemp);
  const [cooling, setCooling] = useState(PRESETS.healthy.cooling);
  const [policyPack, setPolicyPack] = useState("cold_chain");

  const applyPreset = (key: PresetKey) => {
    const p = PRESETS[key];
    setPreset(key);
    setCargoTemp(p.cargoTemp);
    setAmbientTemp(p.ambientTemp);
    setCooling(p.cooling);
  };

  const submit = (e: FormEvent) => {
    e.preventDefault();
    const p = PRESETS[preset];
    evaluateShipment({
      vehicle_id: vehicleId || "TRUCK-042",
      cargo_temperature: cargoTemp,
      ambient_temperature: ambientTemp,
      cooling_status: cooling,
      policy_pack: policyPack,
      dwell_minutes: p.dwellMinutes,
      agent_b_disabled: !!p.agentBDisabled,
      corrupt_critic: !!p.corruptCritic,
      stale_signal: p.staleSignal ?? null,
    });
    setShipmentId(newShipmentId());
  };

  return (
    <form className="panel shipment-form" onSubmit={submit}>
      <div className="shipment-form-head">
        <div>
          <h2>Shipment Evaluation</h2>
          <p className="panel-sub">
            Submit a shipment to the Harness Runtime — the same agents, Trust Gate, Risk
            Assessment Engine, and Decision Authority that run every check on this system.
          </p>
        </div>
        <span className="shipment-id-badge font-mono" title="Operator-facing reference only — not persisted server-side">
          {shipmentId}
        </span>
      </div>

      <div className="shipment-form-grid">
        <label className="field">
          <span className="field-label">Scenario</span>
          <select className="select" value={preset} onChange={(e) => applyPreset(e.target.value as PresetKey)}>
            {(Object.keys(PRESETS) as PresetKey[]).map((key) => (
              <option key={key} value={key}>{PRESETS[key].label}</option>
            ))}
          </select>
        </label>

        <label className="field">
          <span className="field-label">Vehicle ID</span>
          <input className="text-input" value={vehicleId} onChange={(e) => setVehicleId(e.target.value)} />
        </label>

        <label className="field">
          <span className="field-label">Cargo Temperature (°C)</span>
          <input
            className="text-input" type="number" step="0.1" value={cargoTemp}
            onChange={(e) => setCargoTemp(parseFloat(e.target.value) || 0)}
          />
        </label>

        <label className="field">
          <span className="field-label">Ambient Temperature (°C)</span>
          <input
            className="text-input" type="number" step="0.1" value={ambientTemp}
            onChange={(e) => setAmbientTemp(parseFloat(e.target.value) || 0)}
          />
        </label>

        <label className="field">
          <span className="field-label">Cooling Status</span>
          <select className="select" value={cooling ? "on" : "off"} onChange={(e) => setCooling(e.target.value === "on")}>
            <option value="on">On</option>
            <option value="off">Off</option>
          </select>
        </label>

        <label className="field">
          <span className="field-label">Policy Pack</span>
          <select className="select" value={policyPack} onChange={(e) => setPolicyPack(e.target.value)}>
            <option value="cold_chain">Cold Chain</option>
            <option value="tyre_safety">Tyre Safety</option>
          </select>
        </label>
      </div>

      <div className="shipment-form-foot">
        <span className="shipment-preset-hint">{PRESETS[preset].hint}</span>
        <button className="btn-evaluate" type="submit" disabled={busy}>
          <PlayIcon size={14} /> {busy ? "Evaluating…" : "Evaluate Shipment"}
        </button>
      </div>
    </form>
  );
}
