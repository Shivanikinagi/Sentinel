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
from typing import Any

from . import policy
from .config import Settings, get_settings
from .schemas import AgentSource, DecisionStep, Evidence, FreshnessStatus


@dataclass
class GateResult:
    trusted: list[Evidence] = field(default_factory=list)
    excluded: list[Evidence] = field(default_factory=list)
    excluded_ids: list[str] = field(default_factory=list)
    gate_notes: list[str] = field(default_factory=list)
    agents_reporting: list[AgentSource] = field(default_factory=list)
    agents_unavailable: list[AgentSource] = field(default_factory=list)
    missing_required: list[str] = field(default_factory=list)
    stage_results: list[DecisionStep] = field(default_factory=list)

    @property
    def all_evidence(self) -> list[Evidence]:
        return self.trusted + self.excluded


def evaluate(
    evidence: list[Evidence],
    unavailable: list[AgentSource] | None = None,
    *,
    now: datetime | None = None,
    settings: Settings | None = None,
    policy_pack: Any = None,
) -> GateResult:
    """The Trust Gate, split into four single-purpose stages:

      1. Schema Validator  — evidence is already a validated Pydantic `Evidence`
         by the time it reaches the gate; this stage just accounts for that.
      2. Freshness Checker  — recompute age from the timestamp, exclude stale/invalid.
      3. Provenance Checker — each signal must come from its authorized source agent.
      4. Evidence Normalizer — dedupe to the single freshest trusted reading per signal.

    `policy_pack` lets the Supervisor swap in a different domain's provenance
    map / freshness bands / required signals (see policy_packs.py); omitting it
    preserves the original cold-chain-only behaviour exactly.
    """
    settings = settings or get_settings()
    now = now or datetime.now(timezone.utc)
    unavailable = list(unavailable or [])
    pol = policy_pack or policy

    result = GateResult(agents_unavailable=unavailable)
    reporting: set[AgentSource] = set()

    for ev in evidence:
        age = max(0.0, (now - ev.timestamp).total_seconds())
        status = pol.classify_freshness(
            age, settings.fresh_max_seconds, settings.stale_max_seconds
        )
        # Work on a copy so the immutable original record is never mutated.
        graded = ev.model_copy(update={"age_seconds": round(age, 1), "status": status})
        reporting.add(graded.source)

        expected = pol.authorized_source(graded.signal)
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
        s for s in pol.required_signals() if s not in trusted_signals
    ]
    for s in result.missing_required:
        result.gate_notes.append(f"required signal missing or untrusted: {s}")
    for agent in unavailable:
        result.gate_notes.append(f"agent unavailable: {agent.value}")

    result.stage_results = _stage_summary(evidence, result)
    return result


def _stage_summary(evidence: list[Evidence], result: GateResult) -> list[DecisionStep]:
    """Post-hoc breakdown of the same exclusions the loop above already made,
    grouped by which of the four stages is responsible — built by inspecting
    the recorded notes rather than re-running the checks."""
    freshness_excluded = [n for n in result.gate_notes if ": stale" in n or ": invalid" in n]
    provenance_excluded = [n for n in result.gate_notes
                           if "wrong source" in n or "unknown signal" in n]
    normalized = [n for n in result.gate_notes if "superseded" in n]

    return [
        DecisionStep(
            step_name="schema_validator", status="OK",
            detail=f"{len(evidence)} evidence records schema-valid",
        ),
        DecisionStep(
            step_name="freshness_checker",
            status="WARNING" if freshness_excluded else "OK",
            detail=f"{len(freshness_excluded)} excluded as stale/invalid",
        ),
        DecisionStep(
            step_name="provenance_checker",
            status="WARNING" if provenance_excluded else "OK",
            detail=f"{len(provenance_excluded)} excluded on provenance (wrong source/unknown signal)",
        ),
        DecisionStep(
            step_name="evidence_normalizer",
            status="WARNING" if normalized else "OK",
            detail=f"{len(normalized)} superseded duplicate reading(s) removed",
        ),
    ]


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
