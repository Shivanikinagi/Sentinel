"""Phase 0: the persistence foundation actually persists."""
from __future__ import annotations

import threading

from app.audit import Audit, AuditEvent
from app.store import Store


def test_evidence_roundtrip(store: Store) -> None:
    records = [
        {"evidence_id": "ev_1", "run_id": "r1", "signal": "cargo_temperature",
         "source": "agent_a", "value": 4.0},
        {"evidence_id": "ev_2", "run_id": "r1", "signal": "ambient_temperature",
         "source": "agent_b", "value": 22.0},
    ]
    store.insert_evidence(records)
    got = store.get_evidence_for_run("r1")
    assert {e["evidence_id"] for e in got} == {"ev_1", "ev_2"}
    assert got[0]["value"] in (4.0, 22.0)


def test_evidence_is_immutable_insert_or_ignore(store: Store) -> None:
    store.insert_evidence([{"evidence_id": "ev_1", "run_id": "r1",
                            "signal": "s", "source": "agent_a", "value": 1.0}])
    # a second write with the same id must NOT overwrite (evidence is immutable)
    store.insert_evidence([{"evidence_id": "ev_1", "run_id": "r1",
                            "signal": "s", "source": "agent_a", "value": 999.0}])
    got = store.get_evidence_for_run("r1")
    assert len(got) == 1 and got[0]["value"] == 1.0


def test_decision_upsert_and_get(store: Store) -> None:
    decision = {"run_id": "r1", "vehicle_id": "TRUCK-042",
                "controller_state": "AUTO_OPTIMIZE", "confidence": 1.0,
                "critic_rejected": False, "timestamp": "2026-09-02T10:00:00+00:00"}
    store.upsert_decision(decision)
    got = store.get_decision("r1")
    assert got["controller_state"] == "AUTO_OPTIMIZE"
    assert store.list_recent_decisions()[0]["run_id"] == "r1"


def test_audit_is_append_only_and_ordered(store: Store) -> None:
    audit = Audit(store)
    audit.record(AuditEvent.RUN_STARTED, {"scenario": "healthy"}, run_id="r1")
    audit.record(AuditEvent.DECISION_MADE, {"state": "AUTO_OPTIMIZE"}, run_id="r1")
    recent = audit.recent()
    assert [r["event_type"] for r in recent] == [
        AuditEvent.DECISION_MADE, AuditEvent.RUN_STARTED,  # newest first
    ]
    assert recent[0]["payload"]["state"] == "AUTO_OPTIMIZE"


def test_concurrent_reads_and_writes_never_crash_or_corrupt(store: Store) -> None:
    """Regression: a read (recent_audit) racing a write (append_audit) on the
    same sqlite3.Connection came back with payload_json=NULL and crashed
    json.loads() — found by scripts/fuzz_api.py under concurrent load. Every
    Store method must serialize through the same lock, reads included."""
    audit = Audit(store)
    errors: list[Exception] = []
    stop = threading.Event()

    def writer() -> None:
        i = 0
        while not stop.is_set():
            audit.record(AuditEvent.RUN_STARTED, {"i": i}, run_id=f"r{i}")
            i += 1

    def reader() -> None:
        while not stop.is_set():
            try:
                for rec in audit.recent(limit=20):
                    assert isinstance(rec["payload"], dict)  # never None
            except Exception as e:  # noqa: BLE001 - want to see ANY crash
                errors.append(e)

    threads = [threading.Thread(target=writer) for _ in range(4)]
    threads += [threading.Thread(target=reader) for _ in range(4)]
    for t in threads:
        t.start()
    stop.wait(1.0)
    stop.set()
    for t in threads:
        t.join(timeout=5)

    assert errors == [], f"concurrent access raised: {errors}"


def test_action_lifecycle_rows(store: Store) -> None:
    action = {"action_id": "act_1", "run_id": "r1", "action_type": "halt_automation",
              "tier": "HUMAN", "status": "PENDING_APPROVAL"}
    store.insert_action(action)
    store.append_action_event("act_1", to_status="PENDING_APPROVAL")
    assert store.list_actions(status="PENDING_APPROVAL")[0]["action_id"] == "act_1"

    action = {**action, "status": "APPROVED", "approver": "ops@fleet"}
    store.update_action(action)
    store.append_action_event("act_1", to_status="APPROVED",
                              from_status="PENDING_APPROVAL", actor="ops@fleet")
    assert store.get_action("act_1")["status"] == "APPROVED"
    assert store.list_actions(status="PENDING_APPROVAL") == []
    events = store.action_events("act_1")
    assert [e["to_status"] for e in events] == ["PENDING_APPROVAL", "APPROVED"]
