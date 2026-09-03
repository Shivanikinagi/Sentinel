"""SQLite persistence — a thin, append-only repository.

Design rules:
  * The audit table is append-only: rows are never UPDATEd or DELETEd.
  * Evidence is immutable once written (corrections are new rows, per the model).
  * Everything needed to REPLAY a run (raw evidence + full decision + trace) is
    stored, which is what makes the [FUTURE] replay feature nearly free.

The Store keeps a single connection (check_same_thread=False) guarded by a lock,
which is plenty for a single-process demo/hackathon service. It speaks plain
JSON-serializable dicts so it stays decoupled from the Pydantic schema layer.

EVERY method that touches self._conn — reads included — takes self._lock. A
single sqlite3.Connection is not safe for unsynchronized concurrent use from
multiple threads: concurrent-request fuzzing (scripts/fuzz_api.py) reproduced a
read racing a write and coming back with a NULL payload column, crashing
json.loads(). Cursor.fetchall() happens INSIDE the lock; only the pure-Python
json.loads() happens outside it, so the lock is held only for the actual I/O.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, Optional

from .config import get_settings


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


_SCHEMA = """
CREATE TABLE IF NOT EXISTS evidence (
    evidence_id TEXT PRIMARY KEY,
    run_id      TEXT NOT NULL,
    signal      TEXT NOT NULL,
    source      TEXT NOT NULL,
    data_json   TEXT NOT NULL,
    created_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_evidence_run ON evidence(run_id);

CREATE TABLE IF NOT EXISTS decisions (
    run_id          TEXT PRIMARY KEY,
    vehicle_id      TEXT,
    controller_state TEXT NOT NULL,
    confidence      REAL NOT NULL,
    critic_rejected INTEGER NOT NULL,
    data_json       TEXT NOT NULL,
    created_at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_decisions_created ON decisions(created_at);

CREATE TABLE IF NOT EXISTS audit (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    ts           TEXT NOT NULL,
    run_id       TEXT,
    event_type   TEXT NOT NULL,
    payload_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_audit_run ON audit(run_id);

CREATE TABLE IF NOT EXISTS actions (
    action_id       TEXT PRIMARY KEY,
    run_id          TEXT NOT NULL,
    action_type     TEXT NOT NULL,
    tier            TEXT NOT NULL,
    status          TEXT NOT NULL,
    approver        TEXT,
    reason          TEXT,
    data_json       TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_actions_status ON actions(status);

CREATE TABLE IF NOT EXISTS action_events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    action_id   TEXT NOT NULL,
    ts          TEXT NOT NULL,
    from_status TEXT,
    to_status   TEXT NOT NULL,
    actor       TEXT,
    note        TEXT
);
CREATE INDEX IF NOT EXISTS idx_action_events_action ON action_events(action_id);
"""


class Store:
    def __init__(self, db_path: str) -> None:
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        if db_path != ":memory:":
            self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.execute("PRAGMA foreign_keys=ON;")
        self._init_db()

    def _init_db(self) -> None:
        with self._lock:
            self._conn.executescript(_SCHEMA)
            self._conn.commit()

    # ------------------------------------------------------------------ evidence
    def insert_evidence(self, records: list[dict[str, Any]]) -> None:
        if not records:
            return
        rows = [
            (
                r["evidence_id"], r["run_id"], r["signal"], r["source"],
                json.dumps(r), _now_iso(),
            )
            for r in records
        ]
        with self._lock:
            self._conn.executemany(
                "INSERT OR IGNORE INTO evidence "
                "(evidence_id, run_id, signal, source, data_json, created_at) "
                "VALUES (?,?,?,?,?,?)",
                rows,
            )
            self._conn.commit()

    def get_evidence_for_run(self, run_id: str) -> list[dict[str, Any]]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT data_json FROM evidence WHERE run_id=? ORDER BY created_at",
                (run_id,),
            )
            rows = cur.fetchall()
        return [json.loads(row["data_json"]) for row in rows]

    # ----------------------------------------------------------------- decisions
    def upsert_decision(self, decision: dict[str, Any]) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO decisions "
                "(run_id, vehicle_id, controller_state, confidence, critic_rejected, "
                " data_json, created_at) VALUES (?,?,?,?,?,?,?)",
                (
                    decision["run_id"],
                    decision.get("vehicle_id"),
                    decision["controller_state"],
                    float(decision.get("confidence", 0.0)),
                    1 if decision.get("critic_rejected") else 0,
                    json.dumps(decision),
                    decision.get("timestamp") or _now_iso(),
                ),
            )
            self._conn.commit()

    def get_decision(self, run_id: str) -> Optional[dict[str, Any]]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT data_json FROM decisions WHERE run_id=?", (run_id,)
            )
            row = cur.fetchone()
        return json.loads(row["data_json"]) if row else None

    def list_recent_decisions(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT data_json FROM decisions ORDER BY created_at DESC LIMIT ?",
                (limit,),
            )
            rows = cur.fetchall()
        return [json.loads(row["data_json"]) for row in rows]

    # --------------------------------------------------------------------- audit
    def append_audit(
        self, event_type: str, payload: dict[str, Any], run_id: str | None = None
    ) -> int:
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO audit (ts, run_id, event_type, payload_json) "
                "VALUES (?,?,?,?)",
                (_now_iso(), run_id, event_type, json.dumps(payload)),
            )
            self._conn.commit()
            return int(cur.lastrowid)

    def recent_audit(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT id, ts, run_id, event_type, payload_json FROM audit "
                "ORDER BY id DESC LIMIT ?",
                (limit,),
            )
            rows = cur.fetchall()
        return [
            {
                "id": row["id"], "ts": row["ts"], "run_id": row["run_id"],
                "event_type": row["event_type"],
                "payload": json.loads(row["payload_json"]),
            }
            for row in rows
        ]

    # ------------------------------------------------------------------- actions
    def insert_action(self, action: dict[str, Any]) -> None:
        now = _now_iso()
        with self._lock:
            self._conn.execute(
                "INSERT INTO actions "
                "(action_id, run_id, action_type, tier, status, approver, reason, "
                " data_json, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (
                    action["action_id"], action["run_id"], action["action_type"],
                    action["tier"], action["status"], action.get("approver"),
                    action.get("reason"), json.dumps(action),
                    action.get("created_at") or now, now,
                ),
            )
            self._conn.commit()

    def update_action(self, action: dict[str, Any]) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE actions SET status=?, approver=?, reason=?, data_json=?, "
                "updated_at=? WHERE action_id=?",
                (
                    action["status"], action.get("approver"), action.get("reason"),
                    json.dumps(action), _now_iso(), action["action_id"],
                ),
            )
            self._conn.commit()

    def get_action(self, action_id: str) -> Optional[dict[str, Any]]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT data_json FROM actions WHERE action_id=?", (action_id,)
            )
            row = cur.fetchone()
        return json.loads(row["data_json"]) if row else None

    def list_actions(self, status: str | None = None) -> list[dict[str, Any]]:
        with self._lock:
            if status:
                cur = self._conn.execute(
                    "SELECT data_json FROM actions WHERE status=? ORDER BY created_at DESC",
                    (status,),
                )
            else:
                cur = self._conn.execute(
                    "SELECT data_json FROM actions ORDER BY created_at DESC"
                )
            rows = cur.fetchall()
        return [json.loads(row["data_json"]) for row in rows]

    def append_action_event(
        self, action_id: str, to_status: str, from_status: str | None = None,
        actor: str | None = None, note: str | None = None,
    ) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO action_events "
                "(action_id, ts, from_status, to_status, actor, note) "
                "VALUES (?,?,?,?,?,?)",
                (action_id, _now_iso(), from_status, to_status, actor, note),
            )
            self._conn.commit()

    def action_events(self, action_id: str) -> list[dict[str, Any]]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT ts, from_status, to_status, actor, note FROM action_events "
                "WHERE action_id=? ORDER BY id",
                (action_id,),
            )
            rows = cur.fetchall()
        return [dict(row) for row in rows]

    # --------------------------------------------------------------------- admin
    def reset(self) -> None:
        """Wipe all tables. Used by the demo /simulate/reset flow and tests."""
        with self._lock:
            for tbl in ("evidence", "decisions", "audit", "actions", "action_events"):
                self._conn.execute(f"DELETE FROM {tbl}")
            self._conn.commit()

    def close(self) -> None:
        self._conn.close()


@lru_cache
def get_store() -> Store:
    return Store(get_settings().resolved_db_path)
