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
from . import policy
from .schemas import Evidence


@dataclass
class CorrelationResult:
    has_conflicts: bool
    conflicts: list[str]
    evidence_ids: list[str]


class CorrelationEngine:
    def correlate(self, evidence: list[Evidence]) -> CorrelationResult:
        vals = {ev.signal: ev.value for ev in evidence}
        ev_ids = [ev.evidence_id for ev in evidence]
        conflicts: list[str] = []

        cargo = vals.get("cargo_temperature")
        cooling = vals.get("cooling_status")
        ambient = vals.get("ambient_temperature")
        dwell = vals.get("dwell_minutes")

        # Conflict 1: Cooling reported ON while cargo is above safe cold-chain band
        if cargo is not None and cooling == policy.COOLING_ON:
            if cargo > policy.CARGO_TARGET_MAX_C:
                conflicts.append(
                    f"Physical Contradiction: Cooling unit reports ON (1.0) but cargo temperature is {cargo}°C (above safe max {policy.CARGO_TARGET_MAX_C}°C)"
                )

        # Conflict 2: Severe ambient heat with extended dwell
        if ambient is not None and dwell is not None:
            if ambient >= policy.AMBIENT_HIGH_C and dwell >= policy.DWELL_LONG_MIN:
                conflicts.append(
                    f"Thermal Dwell Risk: Ambient temperature is {ambient}°C with extended dwell of {dwell} minutes"
                )

        # Conflict 3: Sensor Drift Anomaly (Sub-zero cargo in 40°C heat without active cooling)
        if cargo is not None and ambient is not None and cooling == policy.COOLING_OFF:
            if ambient >= policy.AMBIENT_HIGH_C and cargo < policy.CARGO_TARGET_MIN_C:
                conflicts.append(
                    f"Sensor Drift Anomaly: Cargo is {cargo}°C in {ambient}°C heat while cooling is OFF"
                )

        return CorrelationResult(
            has_conflicts=len(conflicts) > 0,
            conflicts=conflicts,
            evidence_ids=ev_ids,
        )
