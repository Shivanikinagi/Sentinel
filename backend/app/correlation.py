"""Evidence Correlation Engine — deterministic telemetry cross-validation.

Position in architecture:
  observe -> gate -> CORRELATION -> critic -> verifier -> controller -> gateway

Identifies physical conflicts in telemetry BEFORE the LLM Critic sees data:
1. Cooling status == ON (1.0) while cargo_temperature > safe max (5.0°C).
2. Extreme Ambient temp (>=40°C) with Dwell time (>=30 min) -> Thermal Dwell Risk.
3. High Ambient temp (>=40°C) with Sub-band Cargo temp (<2°C) while cooling is OFF -> Sensor Drift Anomaly.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from . import policy
from .schemas import Evidence

ConflictRule = Callable[[dict], "str | None"]


@dataclass
class CorrelationResult:
    has_conflicts: bool
    conflicts: list[str]
    evidence_ids: list[str]


def _cooling_contradiction(vals: dict) -> str | None:
    cargo, cooling = vals.get("cargo_temperature"), vals.get("cooling_status")
    if cargo is not None and cooling == policy.COOLING_ON and cargo > policy.CARGO_TARGET_MAX_C:
        return (f"Physical Contradiction: Cooling unit reports ON (1.0) but cargo "
                f"temperature is {cargo}°C (above safe max {policy.CARGO_TARGET_MAX_C}°C)")
    return None


def _thermal_dwell(vals: dict) -> str | None:
    ambient, dwell = vals.get("ambient_temperature"), vals.get("dwell_minutes")
    if ambient is not None and dwell is not None:
        if ambient >= policy.AMBIENT_HIGH_C and dwell >= policy.DWELL_LONG_MIN:
            return f"Thermal Dwell Risk: Ambient temperature is {ambient}°C with extended dwell of {dwell} minutes"
    return None


def _sensor_drift(vals: dict) -> str | None:
    cargo, ambient, cooling = vals.get("cargo_temperature"), vals.get("ambient_temperature"), vals.get("cooling_status")
    if cargo is not None and ambient is not None and cooling == policy.COOLING_OFF:
        if ambient >= policy.AMBIENT_HIGH_C and cargo < policy.CARGO_TARGET_MIN_C:
            return f"Sensor Drift Anomaly: Cargo is {cargo}°C in {ambient}°C heat while cooling is OFF"
    return None


# Default (cold-chain) rules — unchanged behaviour when no `rules` override is given.
DEFAULT_RULES: list[ConflictRule] = [_cooling_contradiction, _thermal_dwell, _sensor_drift]


class CorrelationEngine:
    """Evidence Correlation Engine — deterministic physical-conflict checks that
    run BEFORE the critic sees data. `rules` lets a policy pack swap in its own
    conflict checks (see policy_packs.py); omitting it runs the original
    cold-chain rules exactly as before."""

    def correlate(self, evidence: list[Evidence],
                  rules: list[ConflictRule] | None = None) -> CorrelationResult:
        vals = {ev.signal: ev.value for ev in evidence}
        ev_ids = [ev.evidence_id for ev in evidence]
        active_rules = rules if rules is not None else DEFAULT_RULES

        conflicts = [msg for rule in active_rules if (msg := rule(vals)) is not None]

        return CorrelationResult(
            has_conflicts=len(conflicts) > 0,
            conflicts=conflicts,
            evidence_ids=ev_ids,
        )
