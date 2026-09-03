"""Two observer agents with isolation enforced by CODE, not prompt text.

Agent A can only read world.vehicle. Agent B can only read world.environment.
Neither holds a reference to the other's data source, to the Critic, or to any
action function. This is the §8.1 isolation guarantee, implemented literally.
"""
from __future__ import annotations

from datetime import timedelta

from .schemas import AgentSource, Evidence, FreshnessStatus, now_utc
from .world import WorldState


class AgentUnavailable(Exception):
    """Raised when an agent is killed via the demo switch."""


def _fresh_evidence(run_id: str, vehicle_id: str, signal: str, value: float,
                    unit: str, source: AgentSource) -> Evidence:
    return Evidence(
        run_id=run_id, vehicle_id=vehicle_id, signal=signal, value=float(value),
        unit=unit, source=source, timestamp=now_utc(), age_seconds=0.0,
        status=FreshnessStatus.FRESH,
    )


class VehicleObserver:
    """Agent A. Scope: internal telemetry only."""
    SOURCE = AgentSource.AGENT_A
    SCOPE = ("cargo_temperature", "tyre_pressure", "tyre_temperature",
             "cooling_status", "vehicle_speed")

    def observe(self, world: WorldState, run_id: str, vehicle_id: str) -> list[Evidence]:
        if world.agent_a_disabled:
            raise AgentUnavailable("agent_a")

        v = world.vehicle
        readings = [
            ("cargo_temperature", v.cargo_temperature, "celsius"),
            ("tyre_pressure", v.tyre_pressure, "psi"),
            ("tyre_temperature", v.tyre_temperature, "celsius"),
            ("cooling_status", v.cooling_status, "state"),
            ("vehicle_speed", v.vehicle_speed, "kmh"),
        ]
        out: list[Evidence] = []
        for signal, value, unit in readings:
            ev = _fresh_evidence(run_id, vehicle_id, signal, value, unit, self.SOURCE)
            # Demo: backdate one signal so the trust gate can exclude it as stale.
            if world.force_stale_signal == signal:
                ev.timestamp = now_utc() - timedelta(minutes=4)
            out.append(ev)
        return out


class EnvironmentObserver:
    """Agent B. Scope: external context only."""
    SOURCE = AgentSource.AGENT_B
    SCOPE = ("ambient_temperature", "weather_severity", "traffic_level", "dwell_minutes")

    def observe(self, world: WorldState, run_id: str, vehicle_id: str) -> list[Evidence]:
        if world.agent_b_disabled:
            raise AgentUnavailable("agent_b")

        e = world.environment
        readings = [
            ("ambient_temperature", e.ambient_temperature, "celsius"),
            ("weather_severity", e.weather_severity, "index"),
            ("traffic_level", e.traffic_level, "index"),
            ("dwell_minutes", e.dwell_minutes, "minutes"),
        ]
        return [
            _fresh_evidence(run_id, vehicle_id, signal, value, unit, self.SOURCE)
            for signal, value, unit in readings
        ]
