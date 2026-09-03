"""Action Gateway (Layer 2) — the Authority boundary.

The ONLY place an operational action can be requested, approved, and executed.

Hard rules:
  * Agents and the Critic hold NO reference to this module (proven by
    test_isolation.py). They cannot import it, construct it, or call it.
  * Only the Controller (via the pipeline) calls `request()`, and only on
    CRITICAL_HALT.
  * A HUMAN-tier action stays PENDING_APPROVAL until a real person approves it.
    AUTO-tier actions may execute immediately (config-gated) — but even then,
    every transition is written to the append-only audit log.
  * "Execute", for this build, means creating an immutable escalation record.
    Nothing touches a real fleet system. [FUTURE] seam: execute() would route to
    a production Action Gateway behind scoped credentials.
"""
from __future__ import annotations

from uuid import uuid4

from .audit import Audit, AuditEvent
from .config import Settings, get_settings
from .schemas import (
    ActionRequest, ActionStatus, ActionType, ApprovalTier, now_utc,
)
from .store import Store

# Which tier each action requires. Escalation records are low-risk; halting
# automation is a real operational intervention and needs a human.
TIER_FOR_ACTION: dict[ActionType, ApprovalTier] = {
    ActionType.CREATE_ESCALATION_RECORD: ApprovalTier.AUTO,
    ActionType.HALT_AUTOMATION: ApprovalTier.HUMAN,
}


class ActionError(Exception):
    """Illegal action transition (e.g. approving something already executed)."""


class ActionGateway:
    def __init__(self, store: Store, audit: Audit,
                 settings: Settings | None = None) -> None:
        self._store = store
        self._audit = audit
        self._settings = settings or get_settings()

    # -- request (Controller only) ------------------------------------------
    def request(self, *, run_id: str, vehicle_id: str, action_type: ActionType,
                reason: str, context: dict | None = None) -> ActionRequest:
        tier = TIER_FOR_ACTION[action_type]
        ar = ActionRequest(
            run_id=run_id, vehicle_id=vehicle_id, action_type=action_type,
            tier=tier, status=ActionStatus.PENDING_APPROVAL, reason=reason,
            context=context or {},
        )
        self._store.insert_action(ar.model_dump(mode="json"))
        self._store.append_action_event(ar.action_id, to_status=ar.status.value)
        self._audit.record(AuditEvent.ACTION_REQUESTED, ar.model_dump(mode="json"),
                           run_id=run_id)

        if tier == ApprovalTier.AUTO and self._settings.auto_approve_auto_tier:
            ar = self._execute(ar, approver="system:auto-tier")
        return ar

    # -- human decisions -----------------------------------------------------
    def approve(self, action_id: str, approver: str) -> ActionRequest:
        ar = self._require(action_id, ActionStatus.PENDING_APPROVAL, "approve")
        ar = self._transition(ar, ActionStatus.APPROVED, approver=approver)
        self._audit.record(AuditEvent.ACTION_APPROVED, ar.model_dump(mode="json"),
                           run_id=ar.run_id)
        return self._execute(ar, approver=approver)

    def reject(self, action_id: str, approver: str, reason: str) -> ActionRequest:
        ar = self._require(action_id, ActionStatus.PENDING_APPROVAL, "reject")
        ar = self._transition(ar, ActionStatus.REJECTED, approver=approver,
                              decision_reason=reason)
        self._audit.record(AuditEvent.ACTION_REJECTED, ar.model_dump(mode="json"),
                           run_id=ar.run_id)
        return ar

    # -- reads ---------------------------------------------------------------
    def get(self, action_id: str) -> ActionRequest | None:
        raw = self._store.get_action(action_id)
        return ActionRequest.model_validate(raw) if raw else None

    def pending(self) -> list[ActionRequest]:
        return [ActionRequest.model_validate(r)
                for r in self._store.list_actions(status=ActionStatus.PENDING_APPROVAL.value)]

    def events(self, action_id: str) -> list[dict]:
        return self._store.action_events(action_id)

    # -- internals -----------------------------------------------------------
    def _execute(self, ar: ActionRequest, approver: str) -> ActionRequest:
        ar = ar.model_copy(update={
            "status": ActionStatus.EXECUTED,
            "escalation_id": f"esc_{uuid4().hex[:12]}",
            "approver": ar.approver or approver,
            "updated_at": now_utc(),
        })
        self._store.update_action(ar.model_dump(mode="json"))
        self._store.append_action_event(
            ar.action_id, to_status=ActionStatus.EXECUTED.value,
            from_status=ActionStatus.APPROVED.value, actor=approver,
            note=f"escalation {ar.escalation_id} created",
        )
        self._audit.record(AuditEvent.ACTION_EXECUTED, ar.model_dump(mode="json"),
                           run_id=ar.run_id)
        return ar

    def _transition(self, ar: ActionRequest, to: ActionStatus, *, approver: str,
                    decision_reason: str | None = None) -> ActionRequest:
        updated = ar.model_copy(update={
            "status": to, "approver": approver,
            "decision_reason": decision_reason, "updated_at": now_utc(),
        })
        self._store.update_action(updated.model_dump(mode="json"))
        self._store.append_action_event(
            ar.action_id, to_status=to.value, from_status=ar.status.value,
            actor=approver, note=decision_reason,
        )
        return updated

    def _require(self, action_id: str, expected: ActionStatus,
                 verb: str) -> ActionRequest:
        ar = self.get(action_id)
        if ar is None:
            raise ActionError(f"cannot {verb}: action {action_id} not found")
        if ar.status != expected:
            raise ActionError(
                f"cannot {verb}: action {action_id} is {ar.status.value}, "
                f"expected {expected.value}"
            )
        return ar
