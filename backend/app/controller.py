"""Deterministic Controller — the authority the LLM never has.

A pure state machine over (gate result, critic result). Three states, first match
wins. The Controller is the ONLY component permitted to request an action, and only
on CRITICAL_HALT. It never guesses: anything incomplete, stale, or malformed lands
on INSUFFICIENT_DATA.
"""
from __future__ import annotations

from dataclasses import dataclass

from . import confidence, policy
from .critic import CriticResult
from .gate import GateResult
from .schemas import ControllerState, RiskLevel, RiskMatrix


@dataclass
class ControllerOutcome:
    state: ControllerState
    reason: str
    confidence: float
    request_action: bool = False
    risk_matrix: RiskMatrix | None = None
    critic_rejected: bool = False


def decide(gate: GateResult, critic: CriticResult) -> ControllerOutcome:
    matrix = critic.matrix
    contradiction = bool(matrix and matrix.contradiction_detected)
    conf = confidence.compute(
        len(gate.trusted), policy.expected_signal_count(), contradiction
    )

    def outcome(state: ControllerState, reason: str, request: bool = False):
        return ControllerOutcome(
            state=state, reason=reason, confidence=conf, request_action=request,
            risk_matrix=matrix, critic_rejected=critic.rejected,
        )

    # 1) An observer is down -> we do not have both halves of the picture.
    if gate.agents_unavailable:
        agents = ", ".join(a.value for a in gate.agents_unavailable)
        return outcome(ControllerState.INSUFFICIENT_DATA,
                       f"agent(s) unavailable: {agents}")

    # 2) The LLM's output failed the contract -> we do not trust it at all.
    if critic.rejected:
        return outcome(ControllerState.INSUFFICIENT_DATA,
                       f"critic output rejected: {critic.rejection_reason}")

    # 3) Required evidence missing or excluded as stale/invalid.
    if gate.missing_required:
        missing = ", ".join(gate.missing_required)
        return outcome(ControllerState.INSUFFICIENT_DATA,
                       f"required evidence missing/untrusted: {missing}")

    # 4) Confirmed risk (or an internal contradiction) -> halt automation, escalate.
    if matrix and (matrix.risk_level == RiskLevel.HIGH or matrix.contradiction_detected):
        driver = "contradiction detected" if matrix.contradiction_detected \
            else "risk_level HIGH"
        return outcome(ControllerState.CRITICAL_HALT,
                       f"halt: {driver}", request=True)

    # 5) Everything healthy and corroborated.
    return outcome(ControllerState.AUTO_OPTIMIZE,
                   "evidence complete and within safe bounds")
