"""Tests for the Harness Runtime additions: Supervisor/RunState wiring, the
RetryEngine around the Risk Assessment Engine, the split Trust Gate stages,
pluggable policy packs, the confidence breakdown, and the metrics/memory
read-side aggregators. All exercised through the same public `Harness.run()`
and HTTP surface the rest of the suite uses, so a regression here is a
regression a judge could actually see."""
from __future__ import annotations

import pytest

from app.config import Settings
from app.critic import MockCritic
from app.memory import TrendEngine
from app.metrics import compute_metrics
from app.pipeline import build_harness
from app.policy_packs import PolicyEngine, TYRE_SAFETY
from app.schemas import ControllerState
from app.store import Store
from app.world import SCENARIOS, WorldState


def _world(name: str = "healthy") -> WorldState:
    w = WorldState()
    preset = SCENARIOS[name]
    for k, v in preset["vehicle"].items():
        setattr(w.vehicle, k, v)
    for k, v in preset["environment"].items():
        setattr(w.environment, k, v)
    w.scenario = name
    return w


@pytest.fixture
def harness():
    store = Store(":memory:")
    h = build_harness(store, Settings(force_mock_critic=True, auto_approve_auto_tier=True))
    yield h
    store.close()


# ------------------------------------------------------------- gate stages
def test_gate_stage_results_cover_all_four_stages(harness) -> None:
    d = harness.run(_world("healthy"))
    names = [s.step_name for s in d.trace.gate_stage_results]
    assert names == ["schema_validator", "freshness_checker",
                     "provenance_checker", "evidence_normalizer"]
    assert all(s.status == "OK" for s in d.trace.gate_stage_results)


def test_gate_stage_results_flag_exclusions(harness) -> None:
    w = _world("healthy")
    w.force_stale_signal = "cargo_temperature"
    d = harness.run(w)
    freshness = next(s for s in d.trace.gate_stage_results if s.step_name == "freshness_checker")
    assert freshness.status == "WARNING"
    assert "1 excluded" in freshness.detail


# --------------------------------------------------------------- retry engine
def test_transient_backend_error_retries_and_recovers(harness) -> None:
    backend = harness.critic.backend
    assert isinstance(backend, MockCritic)
    backend.trigger_transient_error()

    d = harness.run(_world("healthy"))
    assert d.controller_state == ControllerState.AUTO_OPTIMIZE
    assert len(d.trace.retries) == 1
    assert "Attempt 1 failed" in d.trace.retries[0].detail
    retry_step = next(s for s in d.trace.decision_chain
                      if s.step_name == "retry_risk_assessment_engine")
    assert retry_step.status == "WARNING"
    final_step = next(s for s in d.trace.decision_chain
                      if s.step_name == "risk_assessment_engine")
    assert "2 attempts" in final_step.detail


def test_corrupt_critic_is_not_retried(harness) -> None:
    """Corruption is a schema-validation rejection, not a transient backend
    error — retrying it would just fail identically every time, so it must
    NOT trigger the RetryEngine."""
    w = _world("healthy")
    w.corrupt_critic = True
    d = harness.run(w)
    assert d.trace.retries == []
    assert d.controller_state == ControllerState.INSUFFICIENT_DATA


# ----------------------------------------------------------------- policy packs
def test_policy_engine_lists_both_packs() -> None:
    packs = {p.key for p in PolicyEngine().list_packs()}
    assert packs == {"cold_chain", "tyre_safety"}


def test_tyre_safety_pack_changes_required_signals_and_excludes_cold_chain_signals(harness) -> None:
    d = harness.run(_world("healthy"), policy_pack_key="tyre_safety")
    assert d.policy_pack == "tyre_safety"
    # cargo_temperature is not in the tyre_safety signal map -> excluded as unknown
    assert any("cargo_temperature" in n and "unknown signal" in n for n in d.trace.gate_notes)
    assert d.controller_state == ControllerState.AUTO_OPTIMIZE  # tyre signals are healthy


def test_tyre_safety_pack_flags_underinflation_overheating_contradiction(harness) -> None:
    w = _world("healthy")
    w.vehicle.tyre_pressure = 20.0     # below TYRE_PRESSURE_MIN_PSI
    w.vehicle.tyre_temperature = 95.0  # above TYRE_TEMP_CRITICAL_C
    d = harness.run(w, policy_pack_key="tyre_safety")
    assert d.controller_state == ControllerState.CRITICAL_HALT
    assert d.risk_matrix.contradiction_detected is True
    assert "tyre_underinflated_and_overheating" in d.risk_matrix.risk_factors


def test_unknown_policy_pack_falls_back_to_default(harness) -> None:
    d = harness.run(_world("healthy"), policy_pack_key="not_a_real_pack")
    assert d.policy_pack == "cold_chain"


# ------------------------------------------------------------- confidence breakdown
def test_confidence_breakdown_matches_top_level_confidence(harness) -> None:
    d = harness.run(_world("healthy"))
    assert d.confidence_breakdown is not None
    assert d.confidence_breakdown.confidence == d.confidence
    assert d.confidence_breakdown.trusted_count == 9
    assert d.confidence_breakdown.expected_count == 9
    assert all(s.trusted for s in d.confidence_breakdown.signals)


def test_confidence_breakdown_reflects_contradiction_penalty(harness) -> None:
    d = harness.run(_world("compound_risk"))
    assert d.confidence_breakdown.contradiction_detected is True
    assert d.confidence_breakdown.contradiction_penalty == 2


# --------------------------------------------------------------------- metrics
def test_metrics_aggregate_across_runs(harness) -> None:
    harness.run(_world("healthy"))
    harness.run(_world("compound_risk"))
    m = compute_metrics(harness.store)
    assert m.total_runs == 2
    assert m.auto_optimize == 1
    assert m.critical_halt == 1
    assert 0.0 <= m.avg_confidence <= 1.0
    assert m.pending_actions == 1  # the compound_risk halt is awaiting approval


# ----------------------------------------------------------------------- memory
def test_trend_engine_tracks_signal_across_runs(harness) -> None:
    w = _world("healthy")
    harness.run(w)
    w.vehicle.cargo_temperature = 5.0
    harness.run(w)
    w.vehicle.cargo_temperature = 6.0
    harness.run(w)

    trend = TrendEngine(harness.store).trend("TRUCK-042", "cargo_temperature", limit=5)
    assert len(trend.points) == 3
    assert trend.direction == "rising"
    assert trend.delta == pytest.approx(2.0)


def test_trend_engine_insufficient_data_for_unknown_vehicle(harness) -> None:
    harness.run(_world("healthy"))
    trend = TrendEngine(harness.store).trend("GHOST-999", "cargo_temperature")
    assert trend.points == []
    assert trend.direction == "insufficient_data"
