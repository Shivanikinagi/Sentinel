"""Pydantic contracts. Nothing crosses a layer boundary without validating here."""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class FreshnessStatus(str, Enum):
    FRESH = "fresh"      # < 2 min
    STALE = "stale"      # 2-5 min
    INVALID = "invalid"  # > 5 min


class AgentSource(str, Enum):
    AGENT_A = "agent_a"  # vehicle observer
    AGENT_B = "agent_b"  # environment observer


class Provenance(BaseModel):
    sensor_id: str
    ingestion_method: str = "direct_telematics_poll"
    raw_payload_hash: str
    transformations: list[str] = Field(
        default_factory=lambda: ["unit_conversion", "timestamp_normalization"]
    )


class Evidence(BaseModel):
    """Immutable observation. Corrections create new records, never edits."""
    evidence_id: str = Field(default_factory=lambda: f"ev_{uuid4().hex[:12]}")
    run_id: str
    vehicle_id: str
    signal: str
    value: float
    unit: str
    source: AgentSource
    timestamp: datetime = Field(default_factory=now_utc)
    age_seconds: float = 0.0
    status: FreshnessStatus = FreshnessStatus.FRESH
    provenance: Optional[Provenance] = None

    @field_validator("timestamp")
    @classmethod
    def _tz_aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class RiskMatrix(BaseModel):
    """The ONLY thing the Critic is allowed to emit. Strict — extra fields rejected."""
    model_config = {"extra": "forbid"}

    risk_level: RiskLevel
    contradiction_detected: bool
    risk_factors: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    reasoning_summary: str


class VerifierResult(BaseModel):
    valid: bool
    reason: Optional[str] = None
    checks_passed: list[str] = Field(default_factory=list)
    checks_failed: list[str] = Field(default_factory=list)


class DecisionStep(BaseModel):
    step_name: str
    status: str  # "OK" | "WARNING" | "FAILED" | "SKIPPED"
    detail: str
    duration_ms: float = 0.0


class ControllerState(str, Enum):
    AUTO_OPTIMIZE = "AUTO_OPTIMIZE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    CRITICAL_HALT = "CRITICAL_HALT"


class DecisionTrace(BaseModel):
    """Why-this-decision record. Everything the Controller saw."""
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_snapshot: list[Evidence] = Field(default_factory=list)
    excluded_evidence_ids: list[str] = Field(default_factory=list)
    gate_notes: list[str] = Field(default_factory=list)
    agents_reporting: list[AgentSource] = Field(default_factory=list)
    agents_unavailable: list[AgentSource] = Field(default_factory=list)
    correlation_conflicts: list[str] = Field(default_factory=list)
    verifier_result: Optional[VerifierResult] = None
    circuit_breaker_open: bool = False
    decision_chain: list[DecisionStep] = Field(default_factory=list)


class ControllerDecision(BaseModel):
    run_id: str
    vehicle_id: str
    timestamp: datetime = Field(default_factory=now_utc)
    controller_state: ControllerState
    reason: str
    confidence: float  # computed in code, never self-reported by the LLM
    risk_matrix: Optional[RiskMatrix] = None
    critic_rejected: bool = False
    trace: DecisionTrace
    escalation_id: Optional[str] = None



class SimResponse(BaseModel):
    ok: bool
    message: str


# --------------------------------------------------------------- Action Gateway
class ApprovalTier(str, Enum):
    AUTO = "AUTO"      # low-risk, may execute without a human (config-gated)
    HUMAN = "HUMAN"    # requires an explicit human approval before executing


class ActionType(str, Enum):
    CREATE_ESCALATION_RECORD = "create_escalation_record"
    HALT_AUTOMATION = "halt_automation"


class ActionStatus(str, Enum):
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXECUTED = "EXECUTED"


class ActionRequest(BaseModel):
    """An action the Controller asked for. Only the Controller may create these;
    only a human (or, for AUTO tier, config) may move them to EXECUTED."""
    action_id: str = Field(default_factory=lambda: f"act_{uuid4().hex[:12]}")
    run_id: str
    vehicle_id: str
    action_type: ActionType
    tier: ApprovalTier
    status: ActionStatus = ActionStatus.PENDING_APPROVAL
    reason: str                                   # why the Controller requested it
    context: dict = Field(default_factory=dict)   # risk snapshot for the approver
    approver: Optional[str] = None
    decision_reason: Optional[str] = None         # e.g. why it was rejected
    escalation_id: Optional[str] = None           # set once EXECUTED
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)
