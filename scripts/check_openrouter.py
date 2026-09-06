"""Validate the real OpenRouter path end to end.

Reads backend/.env, builds the OpenRouterCritic with your key/model, sends the
compound-risk evidence set, and prints the VALIDATED RiskMatrix (or the exact
error). Use this to confirm your key + model before wiring it into the demo.

    cd backend && .venv/Scripts/python ../scripts/check_openrouter.py

If OPENROUTER_API_KEY is unset it will tell you and exit — the app still runs on
the deterministic MockCritic without it.

Last verified: 2026-09-06.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone

# Ensure `app` is importable whether run from repo root or backend/.
sys.path.insert(0, "backend")

from app.config import get_settings  # noqa: E402
from app.critic import Critic, OpenRouterCritic  # noqa: E402
from app.schemas import AgentSource, Evidence  # noqa: E402

NOW = datetime.now(timezone.utc)


def _ev(signal: str, source: AgentSource, value: float) -> Evidence:
    return Evidence(run_id="probe", vehicle_id="TRUCK-042", signal=signal,
                    value=value, unit="x", source=source, timestamp=NOW)


def main() -> int:
    s = get_settings()
    if not s.openrouter_api_key:
        print("OPENROUTER_API_KEY is not set. Copy backend/.env.example to "
              "backend/.env and add your key. (The app runs on MockCritic without it.)")
        return 1

    print(f"model   : {s.llm_model}")
    print(f"base_url: {s.openrouter_base_url}")
    evidence = [
        _ev("cargo_temperature", AgentSource.AGENT_A, 11.5),
        _ev("cooling_status", AgentSource.AGENT_A, 1.0),
        _ev("ambient_temperature", AgentSource.AGENT_B, 41.0),
        _ev("dwell_minutes", AgentSource.AGENT_B, 37.0),
    ]
    result = Critic(OpenRouterCritic(s)).assess(evidence)

    if result.rejected:
        print(f"\nREJECTED: {result.rejection_reason}")
        print(f"raw: {result.raw}")
        return 2

    m = result.matrix
    print("\nVALIDATED RiskMatrix from the live model:")
    print(f"  risk_level           : {m.risk_level.value}")
    print(f"  contradiction_detected: {m.contradiction_detected}")
    print(f"  risk_factors         : {m.risk_factors}")
    print(f"  reasoning_summary    : {m.reasoning_summary}")
    print("\nOK — the OpenRouter path works and its output passes schema validation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
