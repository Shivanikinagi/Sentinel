"""Consensus Critic — the ONLY LLM in the decision path, and it has no authority.

Guarantees enforced here:
  * The Critic receives ONLY structured, already-gated Evidence. Never raw world
    state, never a tool, never an action function.
  * NOTHING the Critic emits reaches the Controller without passing strict
    RiskMatrix validation (extra="forbid"). Malformed output is REJECTED, not
    coerced -> the Controller sees `rejected=True` and returns INSUFFICIENT_DATA.
  * Provider-agnostic: OpenRouterCritic for real, MockCritic (deterministic) when
    no API key is set, so the demo never depends on the network.
  * A backend error (timeout, bad key, 500) is caught and turned into a rejection,
    so the harness stays up when the model is unavailable.

Corruption injection (`corrupt=True`) skips the backend and feeds a deliberately
malformed payload through the SAME validation path — proving the rejection is real.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol

import httpx
from pydantic import ValidationError

from . import policy
from .config import Settings, get_settings
from .schemas import Evidence, RiskLevel, RiskMatrix


@dataclass
class CriticResult:
    matrix: RiskMatrix | None
    rejected: bool
    backend: str
    rejection_reason: str | None = None
    raw: Any = None  # exactly what the backend returned, for the audit trail


class CriticBackend(Protocol):
    name: str
    def produce(self, evidence: list[Evidence]) -> dict[str, Any]: ...


# --------------------------------------------------------------------------- API
class Critic:
    def __init__(self, backend: CriticBackend) -> None:
        self.backend = backend

    def assess(self, evidence: list[Evidence], *, corrupt: bool = False) -> CriticResult:
        if corrupt:
            # Demo failure #2: force malformed output through real validation.
            return self._validate(_MALFORMED_PAYLOAD, backend="corrupt-injection")
        try:
            raw = self.backend.produce(evidence)
        except Exception as exc:  # network/timeout/bad-key -> reject, don't crash
            return CriticResult(
                matrix=None, rejected=True, backend=self.backend.name,
                rejection_reason=f"backend_error: {exc.__class__.__name__}: {exc}",
                raw=None,
            )
        return self._validate(raw, backend=self.backend.name)

    @staticmethod
    def _validate(raw: Any, backend: str) -> CriticResult:
        try:
            if not isinstance(raw, dict):
                raise ValueError("critic output is not a JSON object")
            matrix = RiskMatrix.model_validate(raw)
        except (ValidationError, ValueError) as exc:
            return CriticResult(
                matrix=None, rejected=True, backend=backend,
                rejection_reason=f"schema_validation_failed: {exc}", raw=raw,
            )
        return CriticResult(matrix=matrix, rejected=False, backend=backend, raw=raw)


# A payload that is valid JSON but violates the RiskMatrix contract: it is missing
# the required `reasoning_summary` AND carries an extra field (extra="forbid").
_MALFORMED_PAYLOAD: dict[str, Any] = {
    "risk_level": "HIGH",
    "contradiction_detected": True,
    "risk_factors": ["cargo_temperature_rising"],
    "confidence": 0.99,  # <- LLM must NOT set confidence; extra field -> rejected
}


# ------------------------------------------------------------------- mock backend
class MockCritic:
    """Deterministic Critic derived from the policy thresholds.

    Produces a schema-shaped dict (so it exercises the same validation path as a
    real model) using ONLY the trusted evidence handed to it.
    """
    name = "mock"

    def produce(self, evidence: list[Evidence]) -> dict[str, Any]:
        vals = {ev.signal: ev.value for ev in evidence}
        cargo = vals.get("cargo_temperature")
        cooling = vals.get("cooling_status")
        ambient = vals.get("ambient_temperature")
        dwell = vals.get("dwell_minutes")

        factors: list[str] = []
        contradiction = False

        if cargo is not None:
            if cargo > policy.CARGO_CRITICAL_C:
                factors.append("cargo_temperature_critical")
            elif cargo > policy.CARGO_WARN_C:
                factors.append("cargo_temperature_rising")
            if cooling == policy.COOLING_ON and cargo > policy.CARGO_TARGET_MAX_C:
                contradiction = True
                factors.append("cooling_on_but_cargo_warm")
        if ambient is not None and ambient >= policy.AMBIENT_HIGH_C:
            factors.append("high_ambient_temperature")
        if dwell is not None and dwell >= policy.DWELL_LONG_MIN:
            factors.append("extended_dwell")

        if contradiction or (cargo is not None and cargo > policy.CARGO_CRITICAL_C):
            level = RiskLevel.HIGH
        elif factors:
            level = RiskLevel.MEDIUM
        else:
            level = RiskLevel.LOW

        missing = [s for s in policy.required_signals() if s not in vals]

        summary = _mock_summary(level, contradiction, factors, cargo, cooling)
        return {
            "risk_level": level.value,
            "contradiction_detected": contradiction,
            "risk_factors": factors,
            "missing_evidence": missing,
            "reasoning_summary": summary,
        }


def _mock_summary(level, contradiction, factors, cargo, cooling) -> str:
    if contradiction:
        return (
            f"Cooling reports ON yet cargo is {cargo}C, above the {policy.CARGO_TARGET_MAX_C}C "
            f"cold-chain band — physically inconsistent. Risk {level.value}."
        )
    if factors:
        return f"Elevated risk from: {', '.join(factors)}. Risk {level.value}."
    return "All trusted signals within cold-chain bounds. Risk LOW."


# ------------------------------------------------------------- openrouter backend
_SYSTEM_PROMPT = """You are the Consensus Critic in a fleet safety harness.
You assess cold-chain risk from ONLY the structured evidence provided. You have no
tools and no authority to act. Do NOT invent signals not present in the evidence.

Respond with a SINGLE JSON object and nothing else, matching EXACTLY this schema
(no extra keys, no confidence field — confidence is computed elsewhere):
{
  "risk_level": "LOW" | "MEDIUM" | "HIGH",
  "contradiction_detected": boolean,
  "risk_factors": string[],
  "missing_evidence": string[],
  "reasoning_summary": string
}
A key contradiction to watch for: cooling_status ON while cargo_temperature is
above the safe band means the reported cooling state is not trustworthy."""


class OpenRouterCritic:
    name = "openrouter"

    def __init__(self, settings: Settings) -> None:
        self._s = settings

    def produce(self, evidence: list[Evidence]) -> dict[str, Any]:
        payload = [
            {"signal": e.signal, "value": e.value, "unit": e.unit,
             "source": e.source.value, "status": e.status.value}
            for e in evidence
        ]
        body = {
            "model": self._s.llm_model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user",
                 "content": "Evidence:\n" + json.dumps(payload, indent=2)},
            ],
        }
        headers = {
            "Authorization": f"Bearer {self._s.openrouter_api_key}",
            # OpenRouter attribution headers (optional, recommended).
            "HTTP-Referer": "https://github.com/fleet-harness",
            "X-Title": "Fleet-Harness",
        }
        with httpx.Client(timeout=self._s.llm_timeout_seconds) as client:
            resp = client.post(
                f"{self._s.openrouter_base_url}/chat/completions",
                json=body, headers=headers,
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
        return _extract_json_object(content)


def _extract_json_object(content: str) -> dict[str, Any]:
    """Parse the first top-level JSON object out of a model response."""
    content = content.strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass
    start, depth = content.find("{"), 0
    if start == -1:
        raise ValueError("no JSON object in critic response")
    for i in range(start, len(content)):
        depth += (content[i] == "{") - (content[i] == "}")
        if depth == 0:
            return json.loads(content[start : i + 1])
    raise ValueError("unbalanced JSON in critic response")


# -------------------------------------------------------------------- factory
def build_critic(settings: Settings | None = None) -> Critic:
    settings = settings or get_settings()
    backend: CriticBackend = (
        MockCritic() if settings.use_mock_critic else OpenRouterCritic(settings)
    )
    return Critic(backend)
