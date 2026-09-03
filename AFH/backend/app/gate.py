"""Trust Gate — the Evidence layer's guardian.

Deterministic. Given raw evidence from the agents (plus which agents were
unavailable), it decides what may be TRUSTED for a safety-critical decision:

  * Freshness  — recompute age from the timestamp; stale/invalid is excluded.
  * Provenance — each signal must come from its authorized source agent.
  * Completeness — required signals must be present AND trusted, else missing.

Nothing here calls an LLM. Every exclusion is recorded with a human-readable note
so the dashboard's "why this decision?" view can explain itself.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from . import policy
from .config import Settings, get_settings
from .schemas import AgentSource, Evidence, FreshnessStatus


@dataclass
class GateResult:
    trusted: list[Evidence] = field(default_factory=list)
    excluded: list[Evidence] = field(default_factory=list)
    excluded_ids: list[str] = field(default_factory=list)
    gate_notes: list[str] = field(default_factory=list)
    agents_reporting: list[AgentSource] = field(default_factory=list)
    agents_unavailable: list[AgentSource] = field(default_factory=list)
    missing_required: list[str] = field(default_factory=list)

    @property
    def all_evidence(self) -> list[Evidence]:
        return self.trusted + self.excluded


def evaluate(
    evidence: list[Evidence],
    unavailable: list[AgentSource] | None = None,
    *,
    now: datetime | None = None,
    settings: Settings | None = None,
) -> GateResult:
    settings = settings or get_settings()
    now = now or datetime.now(timezone.utc)
    unavailable = list(unavailable or [])

    result = GateResult(agents_unavailable=unavailable)
    reporting: set[AgentSource] = set()

    for ev in evidence:
        age = max(0.0, (now - ev.timestamp).total_seconds())
        status = policy.classify_freshness(
            age, settings.fresh_max_seconds, settings.stale_max_seconds
        )
        # Work on a copy so the immutable original record is never mutated.
        graded = ev.model_copy(update={"age_seconds": round(age, 1), "status": status})
        reporting.add(graded.source)

        expected = policy.authorized_source(graded.signal)
        if expected is None:
            _exclude(result, graded, f"{graded.signal}: unknown signal, not in policy")
            continue
        if graded.source != expected:
            _exclude(
                result, graded,
                f"{graded.signal}: wrong source {graded.source.value} "
                f"(expected {expected.value})",
            )
            continue
        if status in (FreshnessStatus.STALE, FreshnessStatus.INVALID):
            _exclude(
                result, graded,
                f"{graded.signal}: {status.value} (age {graded.age_seconds}s)",
            )
            continue

        result.trusted.append(graded)

    _dedupe_by_signal(result)

    result.agents_reporting = sorted(reporting, key=lambda s: s.value)

    trusted_signals = {ev.signal for ev in result.trusted}
    result.missing_required = [
        s for s in policy.required_signals() if s not in trusted_signals
    ]
    for s in result.missing_required:
        result.gate_notes.append(f"required signal missing or untrusted: {s}")
    for agent in unavailable:
        result.gate_notes.append(f"agent unavailable: {agent.value}")

    return result


def _exclude(result: GateResult, ev: Evidence, note: str) -> None:
    result.excluded.append(ev)
    result.excluded_ids.append(ev.evidence_id)
    result.gate_notes.append(note)


def _dedupe_by_signal(result: GateResult) -> None:
    """At most ONE trusted reading per signal (the freshest). This is what makes
    `expected_signal_count()` a real upper bound on trusted evidence — without
    it, a chatty/misbehaving agent emitting the same signal twice could push
    trusted counts (and therefore confidence) above what the fixed denominator
    assumes, which fuzz testing caught pushing confidence past 100%."""
    best: dict[str, Evidence] = {}
    for ev in result.trusted:
        current = best.get(ev.signal)
        if current is None or ev.age_seconds < current.age_seconds:
            best[ev.signal] = ev

    kept_ids = {ev.evidence_id for ev in best.values()}
    superseded = [ev for ev in result.trusted if ev.evidence_id not in kept_ids]
    result.trusted = list(best.values())
    for ev in superseded:
        _exclude(result, ev, f"{ev.signal}: superseded by a fresher reading of "
                             f"the same signal")
