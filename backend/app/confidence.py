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

from .schemas import CompositeConfidence, ConfidenceBreakdown, SignalConfidence

# Correlation conflicts are cold-chain/tyre-safety-specific physical checks, not
# schema violations — each one found costs a fixed slice of policy compliance
# rather than zeroing it out, since a single conflict is meaningful evidence but
# not proof the whole read is untrustworthy.
_CONFLICT_PENALTY = 0.25


def compute(trusted_count: int, expected_count: int, contradiction: bool) -> float:
    if expected_count <= 0:
        return 0.0
    trusted_count = min(trusted_count, expected_count)
    contradicted = 2 if contradiction else 0
    corroborating = max(0, trusted_count - contradicted)
    return round(corroborating / expected_count, 2)


def compute_breakdown(
    trusted_count: int, expected_count: int, contradiction: bool,
    signals: list[SignalConfidence] | None = None,
) -> ConfidenceBreakdown:
    """Same formula as `compute()`, but returns every intermediate value so the
    UI can show the arithmetic (trusted/expected minus the contradiction
    penalty) instead of just the rounded result."""
    conf = compute(trusted_count, expected_count, contradiction)
    clamped = min(trusted_count, expected_count) if expected_count > 0 else 0
    penalty = 2 if contradiction else 0
    corroborating = max(0, clamped - penalty)
    return ConfidenceBreakdown(
        trusted_count=trusted_count, expected_count=expected_count,
        contradiction_detected=contradiction, contradiction_penalty=penalty,
        corroborating_count=corroborating, confidence=conf,
        signals=signals or [],
    )


def compute_composite(
    *, evidence_quality: float, verifier_valid: bool,
    trusted_count: int, excluded_count: int, conflict_count: int,
    historical_reliability: float = 1.0,
) -> CompositeConfidence:
    """Confidence as a product of independently observable system signals,
    each in [0, 1] — not a single number, and never anything the LLM
    self-reports:

        composite = evidence_quality
                   x verifier_score        (1.0 valid, 0.5 invalid)
                   x gate_cleanliness      (trusted / (trusted + excluded))
                   x policy_compliance     (1.0 - 0.25 per correlation conflict, floored at 0)
                   x historical_reliability

    `evidence_quality` is the SAME value as `ControllerDecision.confidence` —
    this doesn't replace that tested formula, it's a second, richer view built
    on top of it plus signals the base formula doesn't see (verifier outcome,
    gate exclusion ratio, correlation conflicts, and the vehicle's recent
    history)."""
    verifier_score = 1.0 if verifier_valid else 0.5

    total_evidence = trusted_count + excluded_count
    gate_cleanliness = trusted_count / total_evidence if total_evidence > 0 else 1.0

    policy_compliance = max(0.0, 1.0 - _CONFLICT_PENALTY * conflict_count)

    composite = (evidence_quality * verifier_score * gate_cleanliness
                * policy_compliance * historical_reliability)
    composite = round(min(1.0, max(0.0, composite)), 3)

    return CompositeConfidence(
        evidence_quality=round(evidence_quality, 3),
        verifier_score=verifier_score,
        gate_cleanliness=round(gate_cleanliness, 3),
        policy_compliance=round(policy_compliance, 3),
        historical_reliability=round(historical_reliability, 3),
        composite=composite,
    )
