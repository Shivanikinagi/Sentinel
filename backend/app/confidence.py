"""Confidence — computed in CODE, never self-reported by the LLM.

Definition (documented and tested):
    expected      = signals a healthy fleet produces (the FIXED denominator)
    contradicted  = 2 if the Critic flagged a contradiction (the inconsistent pair)
    corroborating = max(0, trusted_count - contradicted)
    confidence    = corroborating / expected      (0.0 when expected is 0)

The denominator is fixed at the expected signal count, NOT the trusted count, so
data incompleteness (a killed agent, excluded stale signals) genuinely lowers
confidence instead of cancelling out.

`trusted_count` is clamped to `expected_count` defensively: the gate already
deduplicates so at most one trusted reading exists per signal (see
gate._dedupe_by_signal), which is what makes expected_count a true upper bound.
This clamp is a second line of defense so confidence can never exceed 1.0 even
if that invariant is ever violated upstream — caught by property-based fuzzing.
"""
from __future__ import annotations


def compute(trusted_count: int, expected_count: int, contradiction: bool) -> float:
    if expected_count <= 0:
        return 0.0
    trusted_count = min(trusted_count, expected_count)
    contradicted = 2 if contradiction else 0
    corroborating = max(0, trusted_count - contradicted)
    return round(corroborating / expected_count, 2)
