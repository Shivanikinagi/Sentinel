"""Append-only audit log — a thin, vocabulary-controlled layer over Store.

Every meaningful step in a run writes one audit record. The vocabulary is fixed
here (not free-form strings scattered across the codebase) so the trail is
queryable and a judge can follow the decision chain end to end.
"""
from __future__ import annotations

from typing import Any

from .store import Store


class AuditEvent:
    RUN_STARTED = "run_started"
    EVIDENCE_OBSERVED = "evidence_observed"
    AGENT_UNAVAILABLE = "agent_unavailable"
    GATE_EVALUATED = "gate_evaluated"
    PLANNING_FINISHED = "planning_finished"
    CRITIC_ASSESSED = "critic_assessed"
    CRITIC_REJECTED = "critic_rejected"
    RETRY_ATTEMPTED = "retry_attempted"
    VERIFIER_FEEDBACK_SENT = "verifier_feedback_sent"
    DECISION_MADE = "decision_made"
    RUN_COMPLETED = "run_completed"
    ACTION_REQUESTED = "action_requested"
    ACTION_APPROVED = "action_approved"
    ACTION_REJECTED = "action_rejected"
    ACTION_EXECUTED = "action_executed"
    SIM_TRIGGERED = "sim_triggered"
    SECURITY_PROBE = "security_probe"


class Audit:
    """Records audit events for one Store. Never mutates prior records."""

    def __init__(self, store: Store) -> None:
        self._store = store

    def record(
        self, event_type: str, payload: dict[str, Any], run_id: str | None = None
    ) -> int:
        return self._store.append_audit(event_type, payload, run_id=run_id)

    def recent(self, limit: int = 50) -> list[dict[str, Any]]:
        return self._store.recent_audit(limit)
