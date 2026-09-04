"""Observability — aggregate Harness Runtime metrics over everything persisted
so far. Deliberately reads only from Store (no new counters to keep in sync);
every number here is derivable from data the harness already durably records.
"""
from __future__ import annotations

from .schemas import HarnessMetrics
from .store import Store


def compute_metrics(store: Store, limit: int = 5000) -> HarnessMetrics:
    decisions = store.list_recent_decisions(limit=limit)
    actions = store.list_actions()

    total = len(decisions)
    auto = insufficient = halt = rejected = 0
    evidence_rejected = retries = breaker_trips = 0
    confidence_sum = 0.0
    latency_sum = 0.0

    for d in decisions:
        state = d.get("controller_state")
        auto += state == "AUTO_OPTIMIZE"
        insufficient += state == "INSUFFICIENT_DATA"
        halt += state == "CRITICAL_HALT"
        rejected += bool(d.get("critic_rejected"))
        confidence_sum += float(d.get("confidence") or 0.0)

        trace = d.get("trace") or {}
        evidence_rejected += len(trace.get("excluded_evidence_ids") or [])
        retries += len(trace.get("retries") or [])
        breaker_trips += bool(trace.get("circuit_breaker_open"))
        latency_sum += sum(step.get("duration_ms", 0.0) for step in trace.get("decision_chain") or [])

    action_counts = {"PENDING_APPROVAL": 0, "EXECUTED": 0, "REJECTED": 0}
    for a in actions:
        status = a.get("status")
        if status in action_counts:
            action_counts[status] += 1

    return HarnessMetrics(
        total_runs=total, auto_optimize=auto, insufficient_data=insufficient,
        critical_halt=halt, critic_rejected=rejected, evidence_rejected=evidence_rejected,
        retries=retries, circuit_breaker_trips=breaker_trips,
        pending_actions=action_counts["PENDING_APPROVAL"],
        executed_actions=action_counts["EXECUTED"],
        rejected_actions=action_counts["REJECTED"],
        avg_confidence=round(confidence_sum / total, 3) if total else 0.0,
        avg_latency_ms=round(latency_sum / total, 2) if total else 0.0,
        success_rate=round(auto / total, 3) if total else 0.0,
    )
