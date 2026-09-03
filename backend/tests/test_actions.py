"""Phase 4: the Action Gateway lifecycle and human-in-the-loop approval."""
from __future__ import annotations

import pytest

from app.actions import ActionError, ActionGateway
from app.audit import Audit, AuditEvent
from app.config import Settings
from app.schemas import ActionStatus, ActionType
from app.store import Store


def _gateway(store: Store, auto: bool = True) -> ActionGateway:
    return ActionGateway(store, Audit(store), Settings(auto_approve_auto_tier=auto))


def test_auto_tier_executes_immediately(store: Store) -> None:
    gw = _gateway(store, auto=True)
    ar = gw.request(run_id="r1", vehicle_id="T", reason="low-risk escalation",
                    action_type=ActionType.CREATE_ESCALATION_RECORD, context={})
    assert ar.status == ActionStatus.EXECUTED
    assert ar.escalation_id and ar.escalation_id.startswith("esc_")
    assert gw.pending() == []


def test_auto_tier_waits_when_config_disabled(store: Store) -> None:
    gw = _gateway(store, auto=False)
    ar = gw.request(run_id="r1", vehicle_id="T", reason="escalation",
                    action_type=ActionType.CREATE_ESCALATION_RECORD)
    assert ar.status == ActionStatus.PENDING_APPROVAL


def test_human_tier_requires_approval(store: Store) -> None:
    gw = _gateway(store)
    ar = gw.request(run_id="r1", vehicle_id="T", reason="halt: contradiction",
                    action_type=ActionType.HALT_AUTOMATION,
                    context={"risk_level": "HIGH"})
    assert ar.status == ActionStatus.PENDING_APPROVAL
    assert [p.action_id for p in gw.pending()] == [ar.action_id]

    done = gw.approve(ar.action_id, approver="ops@fleet")
    assert done.status == ActionStatus.EXECUTED
    assert done.approver == "ops@fleet" and done.escalation_id
    assert gw.pending() == []
    transitions = [e["to_status"] for e in gw.events(ar.action_id)]
    assert transitions == ["PENDING_APPROVAL", "APPROVED", "EXECUTED"]


def test_reject_records_reason_and_stops_execution(store: Store) -> None:
    gw = _gateway(store)
    ar = gw.request(run_id="r1", vehicle_id="T", reason="halt",
                    action_type=ActionType.HALT_AUTOMATION)
    out = gw.reject(ar.action_id, approver="ops@fleet", reason="false alarm")
    assert out.status == ActionStatus.REJECTED
    assert out.decision_reason == "false alarm"
    assert out.escalation_id is None


def test_double_approve_is_illegal(store: Store) -> None:
    gw = _gateway(store)
    ar = gw.request(run_id="r1", vehicle_id="T", reason="halt",
                    action_type=ActionType.HALT_AUTOMATION)
    gw.approve(ar.action_id, approver="ops@fleet")
    with pytest.raises(ActionError):
        gw.approve(ar.action_id, approver="ops@fleet")


def test_every_transition_is_audited(store: Store) -> None:
    gw = _gateway(store)
    ar = gw.request(run_id="r1", vehicle_id="T", reason="halt",
                    action_type=ActionType.HALT_AUTOMATION)
    gw.approve(ar.action_id, approver="ops@fleet")
    events = {a["event_type"] for a in Audit(store).recent()}
    assert {AuditEvent.ACTION_REQUESTED, AuditEvent.ACTION_APPROVED,
            AuditEvent.ACTION_EXECUTED} <= events
