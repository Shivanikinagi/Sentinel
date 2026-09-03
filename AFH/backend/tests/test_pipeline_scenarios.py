"""Phase 5: every demo scene, end to end, through the real pipeline."""
from __future__ import annotations

import pytest

from app.config import Settings
from app.pipeline import build_harness
from app.schemas import ActionStatus, AgentSource, ControllerState, RiskLevel
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
    h = build_harness(store, Settings(force_mock_critic=True,
                                      auto_approve_auto_tier=True))
    yield h
    store.close()


def test_healthy_run_auto_optimizes(harness) -> None:
    d = harness.run(_world("healthy"))
    assert d.controller_state == ControllerState.AUTO_OPTIMIZE
    assert d.confidence == 1.0
    assert d.escalation_id is None
    assert d.risk_matrix.risk_level == RiskLevel.LOW
    # persisted + auditable
    assert harness.store.get_decision(d.run_id)["controller_state"] == "AUTO_OPTIMIZE"
    assert harness.store.get_evidence_for_run(d.run_id)
    assert {a["event_type"] for a in harness.store.recent_audit()} >= {
        "run_started", "gate_evaluated", "critic_assessed", "decision_made"}


def test_compound_risk_halts_and_opens_pending_action(harness) -> None:
    d = harness.run(_world("compound_risk"))
    assert d.controller_state == ControllerState.CRITICAL_HALT
    assert d.risk_matrix.contradiction_detected is True
    assert d.escalation_id is not None
    # a HUMAN-tier action is waiting for approval
    pending = harness.gateway.pending()
    assert [p.action_id for p in pending] == [d.escalation_id]
    assert pending[0].status == ActionStatus.PENDING_APPROVAL

    # human approves -> executed with an immutable escalation record
    done = harness.gateway.approve(d.escalation_id, approver="ops@fleet")
    assert done.status == ActionStatus.EXECUTED and done.escalation_id.startswith("esc_")
    assert harness.gateway.pending() == []


def test_killed_agent_is_insufficient_data_not_a_crash(harness) -> None:
    w = _world("healthy")
    w.agent_b_disabled = True          # Live failure #1
    d = harness.run(w)
    assert d.controller_state == ControllerState.INSUFFICIENT_DATA
    assert AgentSource.AGENT_B in d.trace.agents_unavailable
    assert d.escalation_id is None     # never acts on half a picture


def test_corrupt_critic_is_rejected_and_one_shot(harness) -> None:
    w = _world("healthy")
    w.corrupt_critic = True            # Live failure #2
    d1 = harness.run(w)
    assert d1.controller_state == ControllerState.INSUFFICIENT_DATA
    assert d1.critic_rejected is True
    assert d1.risk_matrix is None      # no unvalidated output leaked through
    # switch was consumed -> next run recovers
    d2 = harness.run(w)
    assert d2.controller_state == ControllerState.AUTO_OPTIMIZE


def test_stale_signal_is_excluded_and_forces_insufficient(harness) -> None:
    w = _world("healthy")
    w.force_stale_signal = "cargo_temperature"   # stretch demo
    d = harness.run(w)
    assert d.controller_state == ControllerState.INSUFFICIENT_DATA
    assert "cargo_temperature" in " ".join(d.trace.gate_notes)
    assert len(d.trace.excluded_evidence_ids) == 1
