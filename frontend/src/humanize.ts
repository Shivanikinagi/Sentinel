// Plain-English translations of the harness's internal vocabulary.
//
// The backend's language (agent_a, RiskMatrix, gate notes, controller reasons)
// is written for engineers and judges evaluating the harness design. A fleet
// operator looking at this dashboard shouldn't have to know what any of that
// means. Every function here takes the raw backend string/shape and returns a
// plain sentence a non-technical person would understand; the raw form stays
// available in "technical" view for anyone who wants the underlying detail.

import type { AuditRecord, ControllerState, RiskMatrix } from "./types";

export const SIGNAL_LABELS: Record<string, string> = {
  cargo_temperature: "Cargo Temperature",
  tyre_pressure: "Tyre Pressure",
  tyre_temperature: "Tyre Temperature",
  cooling_status: "Cooling System",
  vehicle_speed: "Vehicle Speed",
  ambient_temperature: "Outside Temperature",
  weather_severity: "Weather",
  traffic_level: "Traffic",
  dwell_minutes: "Time Stopped",
};

export function signalLabel(signal: string): string {
  return SIGNAL_LABELS[signal] ?? prettify(signal);
}

const SEVERITY_SCALE = ["Clear", "Mild", "Stormy", "Severe"];
const TRAFFIC_SCALE = ["Free-flowing", "Light", "Heavy", "Gridlock"];

/** Some signals are 0-3 index scales or booleans, not numbers a reader can
 * interpret on their own — translate those; everything else keeps its raw
 * value + unit (a temperature or a psi reading is already self-explanatory). */
export function signalValue(signal: string, value: number, unit: string): string {
  if (signal === "cooling_status") return value >= 1 ? "Running" : "Off";
  if (signal === "weather_severity") return SEVERITY_SCALE[Math.min(3, Math.max(0, Math.round(value)))];
  if (signal === "traffic_level") return TRAFFIC_SCALE[Math.min(3, Math.max(0, Math.round(value)))];
  return `${value} ${unit}`;
}

export const STEP_LABELS: Record<string, string> = {
  agent_vehicle_observer: "Vehicle Agent",
  agent_environment_observer: "Environment Agent",
  telemetry_observation: "Telemetry Observation",
  trust_gate: "Trust Gate",
  schema_validator: "Schema Validator",
  freshness_checker: "Freshness Checker",
  provenance_checker: "Provenance Checker",
  evidence_normalizer: "Evidence Normalizer",
  evidence_correlation: "Evidence Correlation",
  risk_assessment_engine: "Risk Assessment Engine",
  retry_risk_assessment_engine: "Retry — Risk Assessment Engine",
  verifier_subsystem: "Verifier Sub-System",
  deterministic_controller: "Decision Authority",
}

export function stepLabel(stepName: string): string {
  return STEP_LABELS[stepName] ?? prettify(stepName);
}

// One line each: why this stage exists, not what it does (the label already
// says what). Small addition, meant to be read in passing during a demo.
export const STEP_PURPOSE: Record<string, string> = {
  agent_vehicle_observer: "Reads only the truck's own sensors — cannot see route/weather data.",
  agent_environment_observer: "Reads only route/weather data — cannot see truck sensors.",
  trust_gate: "Prevent bad evidence: exclude stale, wrong-source, or unrecognized signals.",
  schema_validator: "Confirm every reading is a well-formed, typed observation.",
  freshness_checker: "Exclude readings too old to still be trustworthy.",
  provenance_checker: "Exclude readings that didn't come from their authorized sensor.",
  evidence_normalizer: "Keep only the freshest reading per signal — no double-counting.",
  evidence_correlation: "Catch physical contradictions before the AI ever reasons about them.",
  risk_assessment_engine: "Reasoning: turn trusted evidence into a risk assessment.",
  verifier_subsystem: "Catch an AI answer that contradicts the evidence it was given.",
  deterministic_controller: "Final authority: the one place that turns evidence into a decision.",
};

export function stepPurpose(stepName: string): string | undefined {
  return STEP_PURPOSE[stepName];
}

export const SOURCE_META: Record<string, { title: string; sub: string }> = {
  agent_a: { title: "Truck Sensors", sub: "Cargo, tyres, cooling, speed" },
  agent_b: { title: "Route Conditions", sub: "Weather, traffic, temperature" },
};

export const STATE_META: Record<
  ControllerState,
  { headline: string; tone: string }
> = {
  AUTO_OPTIMIZE: { headline: "Everything looks good", tone: "good" },
  INSUFFICIENT_DATA: { headline: "We can't confirm it's safe", tone: "warn" },
  CRITICAL_HALT: { headline: "Stop — risk detected", tone: "bad" },
};

const RISK_FACTOR_LABELS: Record<string, string> = {
  cargo_temperature_critical: "Cargo is dangerously warm",
  cargo_temperature_rising: "Cargo is warming up",
  cooling_on_but_cargo_warm: "Cooling system may have failed",
  high_ambient_temperature: "It's very hot outside",
  extended_dwell: "Truck has been stopped a long time",
};

export function riskFactorLabel(code: string): string {
  return RISK_FACTOR_LABELS[code] ?? prettify(code);
}

const RISK_LEVEL_BASE: Record<string, number> = { LOW: 15, MEDIUM: 50, HIGH: 85 };

/** A single 0-100 risk number for display, derived from the same RiskMatrix
 * fields the rest of the app already reads — not a value the LLM sets
 * itself (risk_level is schema-validated; the score is just a legible
 * rendering of it plus how many factors/contradictions back it up). */
export function riskScore(rm: RiskMatrix | null | undefined, criticRejected: boolean): number {
  if (!rm) return criticRejected ? 70 : 0;
  const base = RISK_LEVEL_BASE[rm.risk_level] ?? 50;
  const factorBump = Math.min(10, rm.risk_factors.length * 3);
  const contradictionBump = rm.contradiction_detected ? 5 : 0;
  return Math.min(100, base + factorBump + contradictionBump);
}

const ACTION_TYPE_LABELS: Record<string, string> = {
  halt_automation: "Pause automated dispatch",
  create_escalation_record: "Log an incident report",
};

export function actionTypeLabel(code: string): string {
  return ACTION_TYPE_LABELS[code] ?? prettify(code);
}

/** Turn a gate note like "cargo_temperature: stale (age 210.0s)" into a sentence. */
export function humanizeGateNote(note: string): string {
  let m = note.match(/^(\w+): superseded by a fresher reading/);
  if (m) return `Got more than one ${signalLabel(m[1])} reading — used the newest.`;

  m = note.match(/^(\w+): (stale|invalid) \(age ([\d.]+)s\)/);
  if (m) {
    const mins = Math.round(Number(m[3]) / 60);
    return m[2] === "stale"
      ? `${signalLabel(m[1])} reading is ${mins} min old — too old to fully trust, still usable.`
      : `${signalLabel(m[1])} reading is over 5 min old — ignored as too old to trust.`;
  }

  m = note.match(/^(\w+): wrong source (\w+) \(expected (\w+)\)/);
  if (m) return `${signalLabel(m[1])} came from the wrong sensor group — ignored for safety.`;

  m = note.match(/^(\w+): unknown signal/);
  if (m) return `Got a reading we don't recognize (${m[1]}) — ignored.`;

  m = note.match(/^required signal missing or untrusted: (\w+)/);
  if (m) return `Missing a trustworthy ${signalLabel(m[1])} reading.`;

  m = note.match(/^agent unavailable: (\w+)/);
  if (m) return `Lost connection to ${SOURCE_META[m[1]]?.title ?? m[1]}.`;

  return prettifySentence(note);
}

/** Turn the controller's machine reason into a sentence a driver/dispatcher reads. */
export function humanizeReason(reason: string): string {
  let m = reason.match(/^agent\(s\) unavailable: (.+)/);
  if (m) {
    const names = m[1].split(",").map((a) => SOURCE_META[a.trim()]?.title ?? a.trim());
    return `Lost connection to ${names.join(" and ")}, so we can't be sure it's safe.`;
  }

  m = reason.match(/^critic output rejected: /);
  if (m) return "The AI's risk assessment didn't come back in a valid format, so we played it safe.";

  m = reason.match(/^required evidence missing\/untrusted: (.+)/);
  if (m) {
    const names = m[1].split(",").map((s) => signalLabel(s.trim()));
    return `Missing trustworthy data for ${names.join(", ")}.`;
  }

  if (reason.startsWith("halt: contradiction detected"))
    return "Two readings don't add up — something may be wrong with the equipment.";
  if (reason.startsWith("halt: risk_level HIGH"))
    return "Conditions have crossed into a dangerous range.";
  if (reason === "evidence complete and within safe bounds")
    return "All readings are in, fresh, and within safe limits.";

  return prettifySentence(reason);
}

const RISK_WORDS: Record<string, string> = { LOW: "low", MEDIUM: "some", HIGH: "high" };

const AUDIT_LABELS: Record<string, (p: Record<string, unknown>) => string> = {
  run_started: (p) => `Started a check (scenario: ${prettify(String(p.scenario ?? ""))}).`,
  evidence_observed: (p) => `Collected ${p.count ?? "?"} sensor readings.`,
  agent_unavailable: (p) => `${SOURCE_META[String(p.agent)]?.title ?? p.agent} didn't respond.`,
  gate_evaluated: (p) => {
    const trusted = Array.isArray(p.trusted) ? p.trusted.length : 0;
    const excluded = Array.isArray(p.excluded_ids) ? p.excluded_ids.length : 0;
    return excluded > 0
      ? `Checked the data: ${trusted} readings trusted, ${excluded} ignored.`
      : `Checked the data: all ${trusted} readings trusted.`;
  },
  critic_assessed: (p) => `AI found ${RISK_WORDS[String(p.risk_level)] ?? "an unknown level of"} risk.`,
  critic_rejected: () => `AI's answer was invalid — ignored it.`,
  decision_made: (p) => {
    const meta = STATE_META[p.controller_state as ControllerState];
    return meta ? `Decision: ${meta.headline}.` : `Decision made.`;
  },
  action_requested: (p) => `Requested approval to ${actionTypeLabel(String(p.action_type)).toLowerCase()}.`,
  action_approved: () => `A person approved the requested action.`,
  action_rejected: () => `A person rejected the requested action.`,
  action_executed: (p) => `Action carried out${p.escalation_id ? ` (record ${p.escalation_id})` : ""}.`,
  security_probe: (p) => (p.blocked ? "Security check passed — no unauthorized path found." : "Security check FAILED."),
  sim_triggered: () => `A test scenario was triggered.`,
};

export function humanizeAudit(record: AuditRecord): string {
  const fn = AUDIT_LABELS[record.event_type];
  try {
    return fn ? fn(record.payload) : prettifySentence(record.event_type);
  } catch {
    return prettifySentence(record.event_type);
  }
}

export function prettify(key: string): string {
  return key
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

function prettifySentence(s: string): string {
  const words = s.replace(/_/g, " ");
  return words.charAt(0).toUpperCase() + words.slice(1);
}

export function relativeTime(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const s = Math.max(0, Math.round(diffMs / 1000));
  if (s < 5) return "just now";
  if (s < 60) return `${s}s ago`;
  const m = Math.round(s / 60);
  if (m < 60) return `${m}m ago`;
  return `${Math.round(m / 60)}h ago`;
}
