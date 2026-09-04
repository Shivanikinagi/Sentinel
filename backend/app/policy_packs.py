"""Policy Engine — the registry that makes `policy.py` one PACK among several,
instead of the only option hardcoded into the Gate/Critic/Controller.

`policy.py` already documented itself as a future OPA/rego seam; this module is
that seam's first real implementation: a `PolicyPack` bundles everything a
domain needs (provenance map, required signals, freshness classification,
correlation rules, and a risk-reasoning function for the mock Critic), and
`PolicyEngine` selects one by key. `gate.evaluate()` and `CorrelationEngine`
already accept an optional pack override — passing none preserves today's
cold-chain-only behaviour byte for byte, so nothing existing breaks.

Two packs ship today: `cold_chain` (the original, default, thoroughly tested
policy) and `tyre_safety` (a second domain built from signals `policy.py`
already carried but never used — tyre_pressure / tyre_temperature — proving
the harness is domain-independent, not cold-chain-specific.)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from . import policy as cold_chain
from .schemas import AgentSource, Evidence, PolicyPackInfo, RiskLevel

CorrelationRule = Callable[[dict[str, float]], "str | None"]
ReasoningFn = Callable[[list[Evidence]], dict[str, Any]]


@dataclass
class PolicyPack:
    key: str
    label: str
    domain: str
    description: str
    signal_source: dict[str, AgentSource]
    required_signals_tuple: tuple[str, ...]
    classify_freshness: Callable
    correlation_rules: list[CorrelationRule]
    reasoning_fn: ReasoningFn

    def authorized_source(self, signal: str) -> AgentSource | None:
        return self.signal_source.get(signal)

    def required_signals(self) -> tuple[str, ...]:
        """Same call shape as `policy.required_signals()` (a function on the
        module) so gate.py/controller.py can treat a PolicyPack and the raw
        `policy` module interchangeably."""
        return self.required_signals_tuple

    def expected_signal_count(self) -> int:
        return len(self.signal_source)

    def info(self) -> PolicyPackInfo:
        return PolicyPackInfo(
            key=self.key, label=self.label, domain=self.domain,
            description=self.description,
            required_signals=list(self.required_signals_tuple),
            signal_count=self.expected_signal_count(),
        )


# --------------------------------------------------------------- cold_chain pack
def _cold_chain_cooling_contradiction(vals: dict[str, float]) -> str | None:
    cargo, cooling = vals.get("cargo_temperature"), vals.get("cooling_status")
    if cargo is not None and cooling == cold_chain.COOLING_ON and cargo > cold_chain.CARGO_TARGET_MAX_C:
        return (f"Physical Contradiction: Cooling unit reports ON (1.0) but cargo "
                f"temperature is {cargo}°C (above safe max {cold_chain.CARGO_TARGET_MAX_C}°C)")
    return None


def _cold_chain_thermal_dwell(vals: dict[str, float]) -> str | None:
    ambient, dwell = vals.get("ambient_temperature"), vals.get("dwell_minutes")
    if ambient is not None and dwell is not None:
        if ambient >= cold_chain.AMBIENT_HIGH_C and dwell >= cold_chain.DWELL_LONG_MIN:
            return f"Thermal Dwell Risk: Ambient temperature is {ambient}°C with extended dwell of {dwell} minutes"
    return None


def _cold_chain_sensor_drift(vals: dict[str, float]) -> str | None:
    cargo, ambient, cooling = (vals.get("cargo_temperature"), vals.get("ambient_temperature"),
                               vals.get("cooling_status"))
    if cargo is not None and ambient is not None and cooling == cold_chain.COOLING_OFF:
        if ambient >= cold_chain.AMBIENT_HIGH_C and cargo < cold_chain.CARGO_TARGET_MIN_C:
            return f"Sensor Drift Anomaly: Cargo is {cargo}°C in {ambient}°C heat while cooling is OFF"
    return None


def _cold_chain_reasoning(evidence: list[Evidence]) -> dict[str, Any]:
    """Extracted, unchanged, from critic.MockCritic.produce — the default pack's
    deterministic risk reasoning."""
    vals = {ev.signal: ev.value for ev in evidence}
    cargo, cooling = vals.get("cargo_temperature"), vals.get("cooling_status")
    ambient, dwell = vals.get("ambient_temperature"), vals.get("dwell_minutes")

    factors: list[str] = []
    contradiction = False
    if cargo is not None:
        if cargo > cold_chain.CARGO_CRITICAL_C:
            factors.append("cargo_temperature_critical")
        elif cargo > cold_chain.CARGO_WARN_C:
            factors.append("cargo_temperature_rising")
        if cooling == cold_chain.COOLING_ON and cargo > cold_chain.CARGO_TARGET_MAX_C:
            contradiction = True
            factors.append("cooling_on_but_cargo_warm")
    if ambient is not None and ambient >= cold_chain.AMBIENT_HIGH_C:
        factors.append("high_ambient_temperature")
    if dwell is not None and dwell >= cold_chain.DWELL_LONG_MIN:
        factors.append("extended_dwell")

    if contradiction or (cargo is not None and cargo > cold_chain.CARGO_CRITICAL_C):
        level = RiskLevel.HIGH
    elif factors:
        level = RiskLevel.MEDIUM
    else:
        level = RiskLevel.LOW

    missing = [s for s in cold_chain.required_signals() if s not in vals]
    if contradiction:
        summary = (f"Cooling reports ON yet cargo is {cargo}C, above the "
                   f"{cold_chain.CARGO_TARGET_MAX_C}C cold-chain band — physically "
                   f"inconsistent. Risk {level.value}.")
    elif factors:
        summary = f"Elevated risk from: {', '.join(factors)}. Risk {level.value}."
    else:
        summary = "All trusted signals within cold-chain bounds. Risk LOW."

    return {
        "risk_level": level.value, "contradiction_detected": contradiction,
        "risk_factors": factors, "missing_evidence": missing,
        "reasoning_summary": summary,
    }


COLD_CHAIN = PolicyPack(
    key="cold_chain", label="Cold Chain Policy", domain="Refrigerated cargo integrity",
    description="Cargo temperature must stay within the cold-chain band; a cooling "
               "unit reporting ON while cargo is warm is a physical contradiction.",
    signal_source=dict(cold_chain.SIGNAL_SOURCE),
    required_signals_tuple=cold_chain.REQUIRED_SIGNALS,
    classify_freshness=cold_chain.classify_freshness,
    correlation_rules=[_cold_chain_cooling_contradiction, _cold_chain_thermal_dwell,
                       _cold_chain_sensor_drift],
    reasoning_fn=_cold_chain_reasoning,
)


# -------------------------------------------------------------- tyre_safety pack
TYRE_PRESSURE_MIN_PSI = 28.0
TYRE_PRESSURE_MAX_PSI = 40.0
TYRE_PRESSURE_CRITICAL_LOW_PSI = 22.0
TYRE_TEMP_WARN_C = 70.0
TYRE_TEMP_CRITICAL_C = 90.0

TYRE_SIGNAL_SOURCE: dict[str, AgentSource] = {
    "tyre_pressure": AgentSource.AGENT_A,
    "tyre_temperature": AgentSource.AGENT_A,
    "vehicle_speed": AgentSource.AGENT_A,
    "ambient_temperature": AgentSource.AGENT_B,
    "traffic_level": AgentSource.AGENT_B,
}
TYRE_REQUIRED_SIGNALS: tuple[str, ...] = ("tyre_pressure", "tyre_temperature", "vehicle_speed")


def _tyre_underinflated_overheating(vals: dict[str, float]) -> str | None:
    pressure, temp = vals.get("tyre_pressure"), vals.get("tyre_temperature")
    if pressure is not None and temp is not None:
        if pressure < TYRE_PRESSURE_MIN_PSI and temp > TYRE_TEMP_WARN_C:
            return (f"Physical Contradiction: Tyre pressure is {pressure}psi "
                    f"(under {TYRE_PRESSURE_MIN_PSI}psi) while tyre temperature is "
                    f"{temp}°C — consistent with a developing blowout, not a cold sensor fault")
    return None


def _tyre_high_speed_heat_soak(vals: dict[str, float]) -> str | None:
    speed, temp, ambient = vals.get("vehicle_speed"), vals.get("tyre_temperature"), vals.get("ambient_temperature")
    if speed is not None and temp is not None and ambient is not None:
        if speed > 90 and temp > TYRE_TEMP_WARN_C and ambient >= 30:
            return (f"Heat Soak Risk: sustained speed {speed}km/h with tyre temperature "
                    f"{temp}°C in {ambient}°C ambient heat")
    return None


def _tyre_safety_reasoning(evidence: list[Evidence]) -> dict[str, Any]:
    vals = {ev.signal: ev.value for ev in evidence}
    pressure, temp = vals.get("tyre_pressure"), vals.get("tyre_temperature")
    speed, ambient = vals.get("vehicle_speed"), vals.get("ambient_temperature")

    factors: list[str] = []
    contradiction = False
    if pressure is not None:
        if pressure < TYRE_PRESSURE_CRITICAL_LOW_PSI:
            factors.append("tyre_pressure_critical_low")
        elif pressure < TYRE_PRESSURE_MIN_PSI:
            factors.append("tyre_pressure_low")
        elif pressure > TYRE_PRESSURE_MAX_PSI:
            factors.append("tyre_pressure_high")
    if temp is not None:
        if temp > TYRE_TEMP_CRITICAL_C:
            factors.append("tyre_temperature_critical")
        elif temp > TYRE_TEMP_WARN_C:
            factors.append("tyre_temperature_elevated")
        if pressure is not None and pressure < TYRE_PRESSURE_MIN_PSI and temp > TYRE_TEMP_WARN_C:
            contradiction = True
            factors.append("tyre_underinflated_and_overheating")
    if speed is not None and speed > 90 and ambient is not None and ambient >= 30:
        factors.append("sustained_high_speed_in_heat")

    if contradiction or (temp is not None and temp > TYRE_TEMP_CRITICAL_C):
        level = RiskLevel.HIGH
    elif factors:
        level = RiskLevel.MEDIUM
    else:
        level = RiskLevel.LOW

    missing = [s for s in TYRE_REQUIRED_SIGNALS if s not in vals]
    if contradiction:
        summary = (f"Tyre pressure {pressure}psi is below the safe minimum "
                   f"{TYRE_PRESSURE_MIN_PSI}psi while temperature is {temp}°C — "
                   f"underinflation-driven heat buildup. Risk {level.value}.")
    elif factors:
        summary = f"Elevated tyre risk from: {', '.join(factors)}. Risk {level.value}."
    else:
        summary = "All trusted tyre signals within safe bounds. Risk LOW."

    return {
        "risk_level": level.value, "contradiction_detected": contradiction,
        "risk_factors": factors, "missing_evidence": missing,
        "reasoning_summary": summary,
    }


TYRE_SAFETY = PolicyPack(
    key="tyre_safety", label="Tyre Safety Policy", domain="Tyre pressure & heat integrity",
    description="Tyre pressure and temperature must stay within safe bounds; low "
               "pressure combined with high temperature is a blowout precursor.",
    signal_source=dict(TYRE_SIGNAL_SOURCE),
    required_signals_tuple=TYRE_REQUIRED_SIGNALS,
    classify_freshness=cold_chain.classify_freshness,  # freshness bands are domain-agnostic
    correlation_rules=[_tyre_underinflated_overheating, _tyre_high_speed_heat_soak],
    reasoning_fn=_tyre_safety_reasoning,
)


REGISTRY: dict[str, PolicyPack] = {p.key: p for p in (COLD_CHAIN, TYRE_SAFETY)}
DEFAULT_PACK_KEY = "cold_chain"


class PolicyEngine:
    def __init__(self, default_key: str = DEFAULT_PACK_KEY) -> None:
        self._default_key = default_key if default_key in REGISTRY else DEFAULT_PACK_KEY

    def get(self, key: str | None) -> PolicyPack:
        return REGISTRY.get(key or self._default_key, REGISTRY[self._default_key])

    def active(self) -> PolicyPack:
        return self.get(self._default_key)

    def set_active(self, key: str) -> PolicyPack:
        if key not in REGISTRY:
            raise KeyError(key)
        self._default_key = key
        return REGISTRY[key]

    def list_packs(self) -> list[PolicyPackInfo]:
        return [p.info() for p in REGISTRY.values()]
