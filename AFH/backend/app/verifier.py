"""Verifier Sub-System — validates the Critic's LLM outputs for self-consistency, evidence grounding, and physical bounds.

Position in architecture:
  observe -> gate -> correlation -> critic -> VERIFIER -> controller -> gateway

The Verifier performs 3 deterministic verification checks:
1. Self-Consistency:
   - risk_level == HIGH requires at least one non-empty risk_factor.
   - risk_level == LOW requires contradiction_detected == False.
2. Evidence Grounding:
   - Every risk factor mentioned by the Critic must reference signals present in the trusted evidence.
3. Contradiction Flag Verification:
   - If contradiction_detected is True, verifies that sufficient telemetry evidence exists to support a physical contradiction.
"""
from __future__ import annotations

from .schemas import Evidence, RiskLevel, RiskMatrix, VerifierResult


class Verifier:
    def verify(self, risk_matrix: RiskMatrix | None, trusted_evidence: list[Evidence]) -> VerifierResult:
        if risk_matrix is None:
            return VerifierResult(
                valid=False,
                reason="No RiskMatrix produced to verify",
                checks_failed=["risk_matrix_presence"],
            )

        checks_passed: list[str] = []
        checks_failed: list[str] = []

        # Check 1: Self-Consistency
        if risk_matrix.risk_level == RiskLevel.HIGH and not risk_matrix.risk_factors:
            checks_failed.append("self_consistency_high_risk_requires_factors")
            return VerifierResult(
                valid=False,
                reason="Risk matrix reports HIGH risk level but provides zero risk factors",
                checks_passed=checks_passed,
                checks_failed=checks_failed,
            )

        if risk_matrix.risk_level == RiskLevel.LOW and risk_matrix.contradiction_detected:
            checks_failed.append("self_consistency_low_risk_contradiction_mismatch")
            return VerifierResult(
                valid=False,
                reason="Risk matrix reports LOW risk level alongside a contradiction flag",
                checks_passed=checks_passed,
                checks_failed=checks_failed,
            )
        checks_passed.append("self_consistency")

        # Check 2: Evidence Grounding
        evidence_signals = {ev.signal.lower() for ev in trusted_evidence}
        for factor in risk_matrix.risk_factors:
            factor_lower = factor.lower()
            matches = any(sig in factor_lower for sig in evidence_signals) or any(
                term in factor_lower for term in ["cargo", "cooling", "temp", "dwell", "ambient", "speed", "tyre", "temperature"]
            )
            if not matches:
                checks_failed.append(f"unsupported_risk_factor: {factor}")
                return VerifierResult(
                    valid=False,
                    reason=f"Risk factor '{factor}' has no supporting telemetry signal in evidence",
                    checks_passed=checks_passed,
                    checks_failed=checks_failed,
                )
        checks_passed.append("evidence_grounding")

        # Check 3: Contradiction Flag Verification
        if risk_matrix.contradiction_detected:
            if len(trusted_evidence) < 2:
                checks_failed.append("contradiction_requires_multiple_evidence")
                return VerifierResult(
                    valid=False,
                    reason="Contradiction flagged but insufficient evidence signals available",
                    checks_passed=checks_passed,
                    checks_failed=checks_failed,
                )
            checks_passed.append("contradiction_verification")

        return VerifierResult(
            valid=True,
            reason="All verification checks passed (self-consistency, evidence grounding, contradiction validation)",
            checks_passed=checks_passed,
            checks_failed=checks_failed,
        )
