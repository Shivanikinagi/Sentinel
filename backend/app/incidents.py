"""Incident Memory — a subsystem distinct from Memory (memory.py's routine
signal trend). Memory answers "is this signal drifting over time?"; Incident
Memory answers "what actually went wrong, and was it resolved?" — a queryable
history of CRITICAL_HALT runs joined with how the resulting action was
resolved (still pending, approved+executed, or rejected).

Nothing new is persisted here — every field already lives in `decisions` and
`actions` (via `escalation_id`); this is a read-side join, same pattern as
`metrics.py` and `memory.py`.
"""
from __future__ import annotations

from .schemas import IncidentRecord
from .store import Store


class IncidentMemory:
    def __init__(self, store: Store) -> None:
        self._store = store

    def list_incidents(self, vehicle_id: str | None = None, limit: int = 20) -> list[IncidentRecord]:
        decisions = self._store.list_recent_decisions(limit=max(limit * 3, 50))
        incidents: list[IncidentRecord] = []

        for d in decisions:
            if d.get("controller_state") != "CRITICAL_HALT":
                continue
            if vehicle_id and d.get("vehicle_id") != vehicle_id:
                continue

            escalation_id = d.get("escalation_id")
            resolution_status = resolved_by = resolved_at = None
            if escalation_id:
                action = self._store.get_action(escalation_id)
                if action:
                    resolution_status = action.get("status")
                    resolved_by = action.get("approver")
                    resolved_at = action.get("updated_at")

            matrix = d.get("risk_matrix") or {}
            incidents.append(IncidentRecord(
                run_id=d["run_id"], vehicle_id=d.get("vehicle_id", ""),
                timestamp=d.get("timestamp"), reason=d.get("reason", ""),
                risk_factors=matrix.get("risk_factors", []),
                confidence=float(d.get("confidence", 0.0)),
                policy_pack=d.get("policy_pack", "cold_chain"),
                escalation_id=escalation_id,
                resolution_status=resolution_status,
                resolved_by=resolved_by, resolved_at=resolved_at,
            ))
            if len(incidents) >= limit:
                break

        return incidents
