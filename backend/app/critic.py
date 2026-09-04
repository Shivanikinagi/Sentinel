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

from .config import Settings, get_settings
from .policy_packs import PolicyPack, COLD_CHAIN
from .schemas import Evidence, RiskMatrix


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
    """Deterministic Critic. Reasoning is delegated to the active policy pack's
    `reasoning_fn` (default: cold_chain) — this class produces a schema-shaped
    dict (so it exercises the same validation path as a real model) and adds a
    one-shot transient-failure switch for demoing the RetryEngine."""
    name = "mock"

    def __init__(self, pack: PolicyPack = COLD_CHAIN) -> None:
        self._pack = pack
        self._force_error_once = False

    def set_pack(self, pack: PolicyPack) -> None:
        """Let the Supervisor swap the active policy pack's reasoning in for
        THIS run, since a per-run pack override (e.g. tyre_safety) must change
        not just what the gate trusts but how the critic reasons about it."""
        self._pack = pack

    def trigger_transient_error(self) -> None:
        """Demo hook: the NEXT produce() call raises once, simulating a network
        blip, so the RetryEngine's second attempt can recover live on stage."""
        self._force_error_once = True

    def produce(self, evidence: list[Evidence]) -> dict[str, Any]:
        if self._force_error_once:
            self._force_error_once = False
            raise RuntimeError("simulated transient network error")
        return self._pack.reasoning_fn(evidence)


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
        headers = {
            "Authorization": f"Bearer {self._s.openrouter_api_key}",
            "HTTP-Referer": "https://github.com/fleet-harness",
            "X-Title": "Fleet-Harness",
        }

        models_to_try = [self._s.llm_model]
        for m in getattr(self._s, "fallback_models", []):
            if m and m not in models_to_try:
                models_to_try.append(m)

        last_exc: Exception | None = None
        with httpx.Client(timeout=self._s.llm_timeout_seconds) as client:
            for model_name in models_to_try:
                body = {
                    "model": model_name,
                    "temperature": 0,
                    "messages": [
                        {"role": "system", "content": _SYSTEM_PROMPT},
                        {"role": "user", "content": "Evidence:\n" + json.dumps(payload, indent=2)},
                    ],
                }
                try:
                    resp = client.post(
                        f"{self._s.openrouter_base_url}/chat/completions",
                        json=body, headers=headers,
                    )
                    resp.raise_for_status()
                    content = resp.json()["choices"][0]["message"]["content"]
                    return _extract_json_object(content)
                except Exception as exc:
                    last_exc = exc
                    continue

        if last_exc:
            raise last_exc
        raise RuntimeError("No models available to produce critic result")



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
def build_critic(settings: Settings | None = None, pack: PolicyPack = COLD_CHAIN) -> Critic:
    settings = settings or get_settings()
    backend: CriticBackend = (
        MockCritic(pack) if settings.use_mock_critic else OpenRouterCritic(settings)
    )
    return Critic(backend)
