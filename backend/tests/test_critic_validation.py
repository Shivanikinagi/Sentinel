"""Phase 2: no Critic output reaches the Controller without passing validation."""
from __future__ import annotations

from datetime import datetime, timezone

from app.critic import Critic, MockCritic
from app.schemas import AgentSource, Evidence, RiskLevel

NOW = datetime(2026, 9, 2, 12, 0, 0, tzinfo=timezone.utc)


def _ev(signal, source, value) -> Evidence:
    return Evidence(run_id="r1", vehicle_id="TRUCK-042", signal=signal, value=value,
                    unit="x", source=source, timestamp=NOW)


def _healthy():
    return [
        _ev("cargo_temperature", AgentSource.AGENT_A, 4.0),
        _ev("cooling_status", AgentSource.AGENT_A, 1.0),
        _ev("ambient_temperature", AgentSource.AGENT_B, 22.0),
    ]


def _compound():
    return [
        _ev("cargo_temperature", AgentSource.AGENT_A, 11.5),
        _ev("cooling_status", AgentSource.AGENT_A, 1.0),   # ON while cargo is warm
        _ev("ambient_temperature", AgentSource.AGENT_B, 41.0),
        _ev("dwell_minutes", AgentSource.AGENT_B, 37.0),
    ]


def test_healthy_is_low_risk_and_valid() -> None:
    res = Critic(MockCritic()).assess(_healthy())
    assert not res.rejected
    assert res.matrix.risk_level == RiskLevel.LOW
    assert res.matrix.contradiction_detected is False


def test_compound_risk_flags_contradiction_and_high() -> None:
    res = Critic(MockCritic()).assess(_compound())
    assert not res.rejected
    assert res.matrix.risk_level == RiskLevel.HIGH
    assert res.matrix.contradiction_detected is True
    assert "cooling_on_but_cargo_warm" in res.matrix.risk_factors


def test_corrupt_output_is_rejected_not_coerced() -> None:
    res = Critic(MockCritic()).assess(_healthy(), corrupt=True)
    assert res.rejected and res.matrix is None
    assert "schema_validation_failed" in res.rejection_reason
    # the raw malformed payload is preserved for the audit trail
    assert res.raw["risk_level"] == "HIGH"


def test_backend_error_becomes_rejection_not_crash() -> None:
    class Exploding:
        name = "boom"
        def produce(self, evidence):
            raise TimeoutError("model unreachable")

    res = Critic(Exploding()).assess(_healthy())
    assert res.rejected and res.matrix is None
    assert "backend_error" in res.rejection_reason


def test_non_object_output_is_rejected() -> None:
    class Stringy:
        name = "stringy"
        def produce(self, evidence):
            return "not a dict"  # type: ignore[return-value]

    res = Critic(Stringy()).assess(_healthy())
    assert res.rejected and "not a JSON object" in res.rejection_reason


def test_extra_field_is_rejected() -> None:
    class Chatty:
        name = "chatty"
        def produce(self, evidence):
            return {"risk_level": "LOW", "contradiction_detected": False,
                    "risk_factors": [], "missing_evidence": [],
                    "reasoning_summary": "ok", "sneaky_extra": 1}

    res = Critic(Chatty()).assess(_healthy())
    assert res.rejected  # extra="forbid" on RiskMatrix
