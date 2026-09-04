"""RunState — the single object every Harness Runtime stage reads and writes.

Before this module, `pipeline.Harness.run()` threaded a chain of ad hoc local
variables (evidence -> GateResult -> CorrelationResult -> CriticResult ->
VerifierResult -> ControllerOutcome) from one stage to the next as plain function
arguments. That is a pipeline, not a harness.

RunState is the shared, mutable execution record the Supervisor owns for the
duration of one run: agents append evidence to it, the gate annotates what it
trusted/excluded, the critic and verifier record their findings, the controller
writes the final decision — all onto the same object. It is also the natural
seam for a future live/streaming run-status view: whatever a mid-run snapshot
of "what has the harness done so far" would show is exactly this object.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .schemas import (
    ActionType,
    AgentSource,
    ConfidenceBreakdown,
    ControllerState,
    DecisionStep,
    Evidence,
    RiskMatrix,
    VerifierResult,
)


class RunStatus(str, Enum):
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class RunState:
    run_id: str
    vehicle_id: str
    policy_pack: str = "cold_chain"
    status: RunStatus = RunStatus.RUNNING

    # -- Evidence layer --------------------------------------------------------
    observed_evidence: list[Evidence] = field(default_factory=list)  # raw, pre-gate
    trusted_evidence: list[Evidence] = field(default_factory=list)
    excluded_evidence: list[Evidence] = field(default_factory=list)
    excluded_evidence_ids: list[str] = field(default_factory=list)
    gate_notes: list[str] = field(default_factory=list)
    gate_stage_results: list[DecisionStep] = field(default_factory=list)
    missing_required: list[str] = field(default_factory=list)
    agents_reporting: list[AgentSource] = field(default_factory=list)
    agents_unavailable: list[AgentSource] = field(default_factory=list)
    completed_agents: list[str] = field(default_factory=list)
    failed_agents: list[str] = field(default_factory=list)

    # -- Intelligence / policy layer --------------------------------------------
    correlation_conflicts: list[str] = field(default_factory=list)
    risk_matrix: RiskMatrix | None = None
    critic_rejected: bool = False
    critic_rejection_reason: str | None = None
    critic_backend: str | None = None
    verifier_result: VerifierResult | None = None
    circuit_breaker_open: bool = False
    retries: list[DecisionStep] = field(default_factory=list)

    # -- Decision layer ----------------------------------------------------------
    confidence: float = 0.0
    confidence_breakdown: ConfidenceBreakdown | None = None
    controller_state: ControllerState | None = None
    decision_reason: str | None = None

    # -- Authority layer (filled in by the Harness after Supervisor.execute) ----
    request_action: bool = False
    action_type: ActionType | None = None
    escalation_id: str | None = None

    # -- Execution trace ----------------------------------------------------------
    trace: list[DecisionStep] = field(default_factory=list)

    def record_step(self, step: DecisionStep) -> None:
        self.trace.append(step)

    def record_retry(self, step: DecisionStep) -> None:
        self.retries.append(step)
        self.trace.append(step)

    @property
    def all_evidence(self) -> list[Evidence]:
        return self.trusted_evidence + self.excluded_evidence
