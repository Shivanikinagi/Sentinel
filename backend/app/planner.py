"""Planner — decides which agents run, and how, before the Supervisor starts them.

Deliberately thin today: both observers always run, and always in parallel,
because their WorldState scopes are provably disjoint (see
test_isolation.py::test_vehicle_observer_cannot_reach_environment_scope). The
value of a separate Planner is the seam it opens, not complexity today — a
future planner could skip an agent the policy pack doesn't need, or run agents
sequentially when they are not provably independent.
"""
from __future__ import annotations

from dataclasses import dataclass

from .agents import EnvironmentObserver, VehicleObserver
from .schemas import AgentSource


@dataclass
class PlannedAgent:
    source: AgentSource
    name: str
    agent: VehicleObserver | EnvironmentObserver


@dataclass
class ExecutionPlan:
    agents: list[PlannedAgent]
    parallel: bool
    rationale: str


class Planner:
    def plan(self, agent_a: VehicleObserver, agent_b: EnvironmentObserver) -> ExecutionPlan:
        return ExecutionPlan(
            agents=[
                PlannedAgent(AgentSource.AGENT_A, "vehicle_observer", agent_a),
                PlannedAgent(AgentSource.AGENT_B, "environment_observer", agent_b),
            ],
            parallel=True,
            rationale="agent_a and agent_b read disjoint WorldState scopes, "
                      "so they are always safe to schedule concurrently",
        )
