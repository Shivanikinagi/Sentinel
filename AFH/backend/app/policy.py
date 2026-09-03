"""Policy layer — deterministic 'what is allowed / what matters'.

This is kept SEPARATE from the controller ('what should happen') on purpose. It is
the cold-chain policy pack: provenance rules, required signals, freshness bands,
and the numeric thresholds the Critic reasons against.

[FUTURE] seam: in production this file becomes an OPA/rego policy bundle. The
function signatures below are the stable interface that would call out to it.
"""
from __future__ import annotations

from .schemas import AgentSource, FreshnessStatus

# --- Provenance: every signal has exactly ONE authorized source agent. ---------
# Gate rejects any evidence whose source does not match. This is provenance, not
# just isolation: even if an agent were compromised into emitting another agent's
# signal, the gate would exclude it.
SIGNAL_SOURCE: dict[str, AgentSource] = {
    # Agent A — vehicle / internal telemetry
    "cargo_temperature": AgentSource.AGENT_A,
    "tyre_pressure": AgentSource.AGENT_A,
    "tyre_temperature": AgentSource.AGENT_A,
    "cooling_status": AgentSource.AGENT_A,
    "vehicle_speed": AgentSource.AGENT_A,
    # Agent B — environment / external context
    "ambient_temperature": AgentSource.AGENT_B,
    "weather_severity": AgentSource.AGENT_B,
    "traffic_level": AgentSource.AGENT_B,
    "dwell_minutes": AgentSource.AGENT_B,
}

# Signals that MUST be present (and trusted) for a valid AUTO_OPTIMIZE decision.
# Deliberately spans both agents, so losing either agent forces INSUFFICIENT_DATA.
REQUIRED_SIGNALS: tuple[str, ...] = (
    "cargo_temperature",   # agent A
    "cooling_status",      # agent A
    "ambient_temperature", # agent B
)

# --- Cold-chain thresholds (used by the Critic to reason; NOT by the gate). ----
CARGO_TARGET_MAX_C = 6.0     # cold-chain target band upper bound
CARGO_WARN_C = 8.0           # above this: elevated risk
CARGO_CRITICAL_C = 10.0      # above this: critical
AMBIENT_HIGH_C = 35.0        # hot enough to stress the cold chain
DWELL_LONG_MIN = 20.0        # extended stop/idle
COOLING_ON = 1.0


def classify_freshness(
    age_seconds: float, fresh_max: int, stale_max: int
) -> FreshnessStatus:
    """fresh < fresh_max <= stale < stale_max <= invalid."""
    if age_seconds < fresh_max:
        return FreshnessStatus.FRESH
    if age_seconds < stale_max:
        return FreshnessStatus.STALE
    return FreshnessStatus.INVALID


def authorized_source(signal: str) -> AgentSource | None:
    return SIGNAL_SOURCE.get(signal)


def required_signals() -> tuple[str, ...]:
    return REQUIRED_SIGNALS


def expected_signal_count() -> int:
    """Total signals a healthy fleet produces — the confidence denominator, so
    that a missing agent or excluded signal genuinely lowers confidence."""
    return len(SIGNAL_SOURCE)
