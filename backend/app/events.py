"""Event Bus — the harness's control flow is a sequence of published events,
not a chain of direct calls into Audit. Audit is now one subscriber among
possibly several; anything else (a future websocket pusher, a metrics
collector, an incident detector) can subscribe without Supervisor or Harness
knowing it exists.

Vocabulary is the SAME string constants as `audit.AuditEvent` — deliberately.
The Event Bus doesn't invent a parallel vocabulary; it's the delivery
mechanism for the vocabulary that already exists, so every event that reaches
the AuditSink lands in the audit table with the exact event_type it always
has (zero change to what's persisted or to any test that reads the audit log).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable

EventHandler = Callable[["Event"], None]


@dataclass
class Event:
    event_type: str
    run_id: str | None
    payload: dict[str, Any] = field(default_factory=dict)
    ts: float = field(default_factory=time.time)


class EventBus:
    """Synchronous pub/sub. The pipeline is synchronous end to end (one HTTP
    request = one run), so handlers run inline, in subscription order — no
    queue, no async, nothing that could reorder audit rows relative to the
    stage that produced them."""

    def __init__(self) -> None:
        self._subscribers: list[EventHandler] = []
        self.recent: list[Event] = []  # small ring buffer, most-recent-first
        self._max_recent = 200

    def subscribe(self, handler: EventHandler) -> None:
        self._subscribers.append(handler)

    def publish(self, event_type: str, run_id: str | None = None,
                payload: dict[str, Any] | None = None) -> Event:
        event = Event(event_type=event_type, run_id=run_id, payload=payload or {})
        self.recent.insert(0, event)
        del self.recent[self._max_recent:]
        for handler in self._subscribers:
            handler(event)
        return event


def audit_sink(audit) -> EventHandler:
    """Build a subscriber that forwards every event to the Audit log,
    unchanged — this is what makes adding the Event Bus a decoupling, not a
    behavior change: the audit table gets exactly what it always got."""
    def handle(event: Event) -> None:
        audit.record(event.event_type, event.payload, run_id=event.run_id)
    return handle
