export type ControllerState =
  | "AUTO_OPTIMIZE"
  | "INSUFFICIENT_DATA"
  | "CRITICAL_HALT";

export type FreshnessStatus = "fresh" | "stale" | "invalid";
export type AgentSource = "agent_a" | "agent_b";

export interface Provenance {
  sensor_id: string;
  ingestion_method: string;
  raw_payload_hash: string;
  transformations: string[];
}

export interface Evidence {
  evidence_id: string;
  run_id: string;
  vehicle_id: string;
  signal: string;
  value: number;
  unit: string;
  source: AgentSource;
  timestamp: string;
  age_seconds: number;
  status: FreshnessStatus;
  provenance?: Provenance;
}

export interface RiskMatrix {
  risk_level: "LOW" | "MEDIUM" | "HIGH";
  contradiction_detected: boolean;
  risk_factors: string[];
  missing_evidence: string[];
  reasoning_summary: string;
}

export interface VerifierResult {
  valid: boolean;
  reason?: string;
  checks_passed: string[];
  checks_failed: string[];
}

export interface DecisionStep {
  step_name: string;
  status: string;
  detail: string;
  duration_ms: number;
}

export interface DecisionTrace {
  evidence_ids: string[];
  evidence_snapshot: Evidence[];
  excluded_evidence_ids: string[];
  gate_notes: string[];
  agents_reporting: AgentSource[];
  agents_unavailable: AgentSource[];
  correlation_conflicts?: string[];
  verifier_result?: VerifierResult;
  circuit_breaker_open?: boolean;
  decision_chain?: DecisionStep[];
}

export interface ControllerDecision {
  run_id: string;
  vehicle_id: string;
  timestamp: string;
  controller_state: ControllerState;
  reason: string;
  confidence: number;
  risk_matrix: RiskMatrix | null;
  critic_rejected: boolean;
  trace: DecisionTrace;
  escalation_id: string | null;
}

export interface ActionRequest {
  action_id: string;
  run_id: string;
  vehicle_id: string;
  action_type: string;
  tier: "AUTO" | "HUMAN";
  status: "PENDING_APPROVAL" | "APPROVED" | "REJECTED" | "EXECUTED";
  reason: string;
  context: Record<string, unknown>;
  approver: string | null;
  escalation_id: string | null;
}

export interface WorldState {
  scenario: string;
  vehicle: Record<string, number>;
  environment: Record<string, number>;
  switches: {
    agent_a_disabled: boolean;
    agent_b_disabled: boolean;
    corrupt_critic: boolean;
    force_stale_signal: string | null;
  };
}

export interface AuditRecord {
  id: number;
  ts: string;
  run_id: string | null;
  event_type: string;
  payload: Record<string, unknown>;
}

export interface ProbeAttempt {
  vector: string;
  outcome: "blocked" | "EXPOSED";
  detail: string;
}

export interface ProbeResult {
  blocked: boolean;
  conclusion: string;
  attempts: ProbeAttempt[];
}
