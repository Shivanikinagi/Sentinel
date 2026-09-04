"""Test suite for Verifier, Correlation Engine, Circuit Breaker, Tool Registry, and Evidence Provenance."""
import pytest
from app.circuit_breaker import CircuitBreaker, CircuitOpenError
from app.correlation import CorrelationEngine
from app.schemas import (
    AgentSource, Evidence, FreshnessStatus, Provenance, RiskLevel, RiskMatrix, now_utc,
)
from app.tools import ToolAccessDeniedError, ToolRegistry
from app.verifier import Verifier


def test_evidence_provenance():
    prov = Provenance(
        sensor_id="snr_agent_a_cargo_temperature",
        ingestion_method="direct_telematics_poll",
        raw_payload_hash="sha256:12345678",
        transformations=["unit_conversion"],
    )
    ev = Evidence(
        run_id="run_test",
        vehicle_id="TRUCK-042",
        signal="cargo_temperature",
        value=11.5,
        unit="celsius",
        source=AgentSource.AGENT_A,
        timestamp=now_utc(),
        provenance=prov,
    )
    assert ev.provenance is not None
    assert ev.provenance.sensor_id == "snr_agent_a_cargo_temperature"
    assert ev.provenance.raw_payload_hash == "sha256:12345678"


def test_verifier_valid_matrix():
    verifier = Verifier()
    ev1 = Evidence(run_id="r", vehicle_id="v", signal="cargo_temperature", value=11.5, unit="c", source=AgentSource.AGENT_A)
    ev2 = Evidence(run_id="r", vehicle_id="v", signal="cooling_status", value=1.0, unit="state", source=AgentSource.AGENT_A)

    matrix = RiskMatrix(
        risk_level=RiskLevel.HIGH,
        contradiction_detected=True,
        risk_factors=["cargo_temperature is elevated above safe band"],
        missing_evidence=[],
        reasoning_summary="Cargo temp high while cooling reported ON",
    )

    res = verifier.verify(matrix, [ev1, ev2])
    assert res.valid is True
    assert len(res.checks_passed) == 3


def test_verifier_inconsistent_high_risk_no_factors():
    verifier = Verifier()
    ev1 = Evidence(run_id="r", vehicle_id="v", signal="cargo_temperature", value=11.5, unit="c", source=AgentSource.AGENT_A)

    matrix = RiskMatrix(
        risk_level=RiskLevel.HIGH,
        contradiction_detected=False,
        risk_factors=[],  # Inconsistent: HIGH risk but zero factors!
        missing_evidence=[],
        reasoning_summary="No reason given",
    )

    res = verifier.verify(matrix, [ev1])
    assert res.valid is False
    assert "self_consistency_high_risk_requires_factors" in res.checks_failed


def test_correlation_engine_physical_contradiction():
    engine = CorrelationEngine()
    ev1 = Evidence(run_id="r", vehicle_id="v", signal="cargo_temperature", value=12.0, unit="c", source=AgentSource.AGENT_A)
    ev2 = Evidence(run_id="r", vehicle_id="v", signal="cooling_status", value=1.0, unit="state", source=AgentSource.AGENT_A)

    res = engine.correlate([ev1, ev2])
    assert res.has_conflicts is True
    assert any("Physical Contradiction" in c for c in res.conflicts)


def test_circuit_breaker_trips_to_open():
    cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=10.0)
    assert cb.is_open() is False

    cb.record_failure()
    cb.record_failure()
    cb.record_failure()

    assert cb.is_open() is True
    with pytest.raises(CircuitOpenError):
        cb.execute(lambda: "should not be called")


def test_tool_registry_access_control():
    reg = ToolRegistry()
    res = reg.execute_tool("agent_a", "get_cargo_telemetry")
    assert res["status"] == "SUCCESS"

    with pytest.raises(ToolAccessDeniedError):
        reg.execute_tool("agent_a", "get_environmental_telemetry")
