"""Phase 3: the full controller decision table, first-match-wins."""
from __future__ import annotations

from datetime import datetime, timezone

from app import controller
from app.critic import CriticResult
from app.gate import GateResult
from app.schemas import (
    AgentSource, ControllerState, Evidence, RiskLevel, RiskMatrix,
)

NOW = datetime(2026, 9, 2, 12, 0, 0, tzinfo=timezone.utc)


def _ev(signal, source=AgentSource.AGENT_A) -> Evidence:
    return Evidence(run_id="r1", vehicle_id="T", signal=signal, value=1.0,
                    unit="x", source=source, timestamp=NOW)


def _trusted(n: int) -> list[Evidence]:
    return [_ev(f"sig_{i}") for i in range(n)]


def _matrix(level=RiskLevel.LOW, contradiction=False) -> RiskMatrix:
    return RiskMatrix(risk_level=level, contradiction_detected=contradiction,
                      reasoning_summary="…")


def _ok_critic(level=RiskLevel.LOW, contradiction=False) -> CriticResult:
    return CriticResult(matrix=_matrix(level, contradiction), rejected=False,
                        backend="mock")


def test_healthy_auto_optimize() -> None:
    gate = GateResult(trusted=_trusted(9))  # all expected signals present
    out = controller.decide(gate, _ok_critic())
    assert out.state == ControllerState.AUTO_OPTIMIZE
    assert out.request_action is False
    assert out.confidence == 1.0


def test_agent_unavailable_wins_over_everything() -> None:
    gate = GateResult(trusted=_trusted(5),
                      agents_unavailable=[AgentSource.AGENT_B])
    # even with a HIGH-risk critic, unavailability short-circuits to INSUFFICIENT
    out = controller.decide(gate, _ok_critic(RiskLevel.HIGH))
    assert out.state == ControllerState.INSUFFICIENT_DATA
    assert "unavailable" in out.reason


def test_critic_rejected_is_insufficient() -> None:
    gate = GateResult(trusted=_trusted(5))
    rejected = CriticResult(matrix=None, rejected=True, backend="mock",
                            rejection_reason="schema_validation_failed: boom")
    out = controller.decide(gate, rejected)
    assert out.state == ControllerState.INSUFFICIENT_DATA
    assert "rejected" in out.reason


def test_missing_required_is_insufficient() -> None:
    gate = GateResult(trusted=_trusted(2), missing_required=["cargo_temperature"])
    out = controller.decide(gate, _ok_critic())
    assert out.state == ControllerState.INSUFFICIENT_DATA
    assert "cargo_temperature" in out.reason


def test_high_risk_triggers_critical_halt_and_action() -> None:
    gate = GateResult(trusted=_trusted(5))
    out = controller.decide(gate, _ok_critic(RiskLevel.HIGH))
    assert out.state == ControllerState.CRITICAL_HALT
    assert out.request_action is True


def test_contradiction_triggers_critical_halt() -> None:
    gate = GateResult(trusted=_trusted(9))
    out = controller.decide(gate, _ok_critic(RiskLevel.MEDIUM, contradiction=True))
    assert out.state == ControllerState.CRITICAL_HALT
    assert out.request_action is True
    assert out.confidence == 0.78  # (9-2)/9


def test_precedence_missing_required_beats_high_risk() -> None:
    # A HIGH-risk matrix must NOT override missing evidence: we still refuse to act.
    gate = GateResult(trusted=_trusted(3), missing_required=["cooling_status"])
    out = controller.decide(gate, _ok_critic(RiskLevel.HIGH))
    assert out.state == ControllerState.INSUFFICIENT_DATA
