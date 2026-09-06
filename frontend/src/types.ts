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
  gate_stage_results?: DecisionStep[];
  agents_reporting: AgentSource[];
  agents_unavailable: AgentSource[];
  correlation_conflicts?: string[];
  verifier_result?: VerifierResult;
  circuit_breaker_open?: boolean;
  decision_chain?: DecisionStep[];
  retries?: DecisionStep[];
  feedback_loop_triggered?: boolean;
  feedback_loop_reason?: string | null;
}

export interface SignalConfidence {
  signal: string;
  trusted: boolean;
  status?: string | null;
}

export interface ConfidenceBreakdown {
  trusted_count: number;
  expected_count: number;
  contradiction_detected: boolean;
  contradiction_penalty: number;
  corroborating_count: number;
  confidence: number;
  signals: SignalConfidence[];
}

export interface CompositeConfidence {
  evidence_quality: number;
  verifier_score: number;
  gate_cleanliness: number;
  policy_compliance: number;
  historical_reliability: number;
  composite: number;
}

export interface ControllerDecision {
  run_id: string;
  vehicle_id: string;
  timestamp: string;
  controller_state: ControllerState;
  reason: string;
  confidence: number;
  confidence_breakdown?: ConfidenceBreakdown | null;
  composite_confidence?: CompositeConfidence | null;
  policy_pack: string;
  risk_matrix: RiskMatrix | null;
  critic_rejected: boolean;
  trace: DecisionTrace;
  escalation_id: string | null;
}

export interface IncidentRecord {
  run_id: string;
  vehicle_id: string;
  timestamp: string;
  reason: string;
  risk_factors: string[];
  confidence: number;
  policy_pack: string;
  escalation_id: string | null;
  resolution_status: string | null;
  resolved_by: string | null;
  resolved_at: string | null;
}

export interface PolicyPackInfo {
  key: string;
  label: string;
  domain: string;
  description: string;
  required_signals: string[];
  signal_count: number;
}

export interface TrendPoint {
  run_id: string;
  timestamp: string;
  value: number;
}

export interface VehicleTrend {
  vehicle_id: string;
  signal: string;
  points: TrendPoint[];
  direction: "rising" | "falling" | "flat" | "insufficient_data";
  delta: number | null;
}

export interface HarnessMetrics {
  total_runs: number;
  auto_optimize: number;
  insufficient_data: number;
  critical_halt: number;
  critic_rejected: number;
  evidence_rejected: number;
  retries: number;
  circuit_breaker_trips: number;
  pending_actions: number;
  executed_actions: number;
  rejected_actions: number;
  avg_confidence: number;
  avg_latency_ms: number;
  success_rate: number;
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

export interface ShipmentInput {
  vehicle_id?: string;
  cargo_temperature?: number;
  ambient_temperature?: number;
  cooling_status?: boolean;
  policy_pack?: string;
  dwell_minutes?: number;
  agent_a_disabled?: boolean;
  agent_b_disabled?: boolean;
  corrupt_critic?: boolean;
  stale_signal?: string | null;
}
