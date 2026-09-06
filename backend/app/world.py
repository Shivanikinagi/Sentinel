"""Mocked fleet world state + demo control switches.

This is the ONLY module that holds raw sensor truth. Agents read their own slice
of it through hard-coded scopes (see agents.py); nothing else touches it directly.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock


@dataclass
class VehicleTruth:
    vehicle_id: str = "TRUCK-042"
    cargo_temperature: float = 4.0      # celsius, cold-chain target ~2-6
    tyre_pressure: float = 34.0         # psi
    tyre_temperature: float = 38.0      # celsius
    cooling_status: float = 1.0         # 1 = ON, 0 = OFF
    vehicle_speed: float = 62.0         # km/h


@dataclass
class EnvironmentTruth:
    ambient_temperature: float = 22.0   # celsius
    weather_severity: float = 0.0       # 0 clear .. 3 severe
    traffic_level: float = 1.0          # 0 free .. 3 gridlock
    dwell_minutes: float = 2.0          # minutes stopped/idling


@dataclass
class WorldState:
    vehicle: VehicleTruth = field(default_factory=VehicleTruth)
    environment: EnvironmentTruth = field(default_factory=EnvironmentTruth)

    # --- demo control switches ---
    agent_a_disabled: bool = False      # kill vehicle observer
    agent_b_disabled: bool = False      # kill environment observer
    corrupt_critic: bool = False        # force malformed Critic output (one-shot)
    force_stale_signal: str | None = None  # name a vehicle signal to backdate

    scenario: str = "healthy"

    _lock: Lock = field(default_factory=Lock, repr=False)


# Scenario presets. Each mutates the truth the agents will observe next run.
SCENARIOS: dict[str, dict] = {
    "healthy": {
        "vehicle": dict(cargo_temperature=4.0, tyre_pressure=34.0,
                        tyre_temperature=38.0, cooling_status=1.0, vehicle_speed=62.0),
        "environment": dict(ambient_temperature=22.0, weather_severity=0.0,
                            traffic_level=1.0, dwell_minutes=2.0),
    },
    # Cooling reports ON while cargo temp climbs, high ambient heat, long dwell.
    "compound_risk": {
        "vehicle": dict(cargo_temperature=11.5, tyre_pressure=33.0,
                        tyre_temperature=41.0, cooling_status=1.0, vehicle_speed=0.0),
        "environment": dict(ambient_temperature=41.0, weather_severity=1.0,
                            traffic_level=3.0, dwell_minutes=37.0),
    },
}

_STATE = WorldState()


def get_state() -> WorldState:
    return _STATE


def apply_scenario(name: str) -> None:
    if name not in SCENARIOS:
        raise KeyError(name)
    preset = SCENARIOS[name]
    with _STATE._lock:
        for k, v in preset["vehicle"].items():
            setattr(_STATE.vehicle, k, v)
        for k, v in preset["environment"].items():
            setattr(_STATE.environment, k, v)
        _STATE.scenario = name


def reset() -> None:
    global _STATE
    _STATE = WorldState()
    apply_scenario("healthy")


def apply_custom(
    *,
    vehicle_id: str | None = None,
    cargo_temperature: float | None = None,
    ambient_temperature: float | None = None,
    cooling_status: bool | None = None,
    dwell_minutes: float | None = None,
    agent_a_disabled: bool = False,
    agent_b_disabled: bool = False,
    corrupt_critic: bool = False,
    stale_signal: str | None = None,
) -> None:
    """Operator-submitted shipment telemetry (Live Scenario Runner).

    Same category of operation as `apply_scenario` / the `/simulate/*` demo
    switches above: it only mutates the raw truth the agents observe next
    run. Unspecified fields fall back to the healthy baseline so every
    submission starts from a clean, repeatable world state; the fault
    switches are set explicitly (not merged) so a previous submission's
    fault never leaks into the next one.
    """
    with _STATE._lock:
        healthy = SCENARIOS["healthy"]
        for k, v in healthy["vehicle"].items():
            setattr(_STATE.vehicle, k, v)
        for k, v in healthy["environment"].items():
            setattr(_STATE.environment, k, v)

        if vehicle_id:
            _STATE.vehicle.vehicle_id = vehicle_id
        if cargo_temperature is not None:
            _STATE.vehicle.cargo_temperature = cargo_temperature
        if cooling_status is not None:
            _STATE.vehicle.cooling_status = 1.0 if cooling_status else 0.0
        if ambient_temperature is not None:
            _STATE.environment.ambient_temperature = ambient_temperature
        if dwell_minutes is not None:
            _STATE.environment.dwell_minutes = dwell_minutes

        _STATE.agent_a_disabled = agent_a_disabled
        _STATE.agent_b_disabled = agent_b_disabled
        if corrupt_critic:
            _STATE.corrupt_critic = True
        _STATE.force_stale_signal = stale_signal
        _STATE.scenario = "custom"
