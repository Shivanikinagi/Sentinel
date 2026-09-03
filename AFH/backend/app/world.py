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
