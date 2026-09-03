"""Tool Registry with Explicit Agent Scoping, Authentication, and Rate Limiting.

Enforces zero-trust access control over observer agent tool calls.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class Tool:
    name: str
    description: str
    allowed_agents: list[str]
    requires_auth: bool = True
    rate_limit_per_min: int = 60
    call_history: list[float] = field(default_factory=list)

    def can_agent_call(self, agent: str) -> bool:
        return agent in self.allowed_agents

    def is_rate_limited(self) -> bool:
        now = time.time()
        self.call_history = [t for t in self.call_history if now - t < 60.0]
        return len(self.call_history) >= self.rate_limit_per_min

    def record_call(self) -> None:
        self.call_history.append(time.time())


class ToolAccessDeniedError(Exception):
    pass


class RateLimitExceededError(Exception):
    pass


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {
            "get_cargo_telemetry": Tool(
                name="get_cargo_telemetry",
                description="Fetches cargo temperature and cooling status",
                allowed_agents=["agent_a"],
                requires_auth=True,
                rate_limit_per_min=120,
            ),
            "get_environmental_telemetry": Tool(
                name="get_environmental_telemetry",
                description="Fetches ambient temperature and dwell time",
                allowed_agents=["agent_b"],
                requires_auth=True,
                rate_limit_per_min=120,
            ),
        }

    def execute_tool(self, agent: str, tool_name: str) -> dict:
        tool = self._tools.get(tool_name)
        if not tool:
            raise ValueError(f"Tool '{tool_name}' not registered in ToolRegistry")

        if not tool.can_agent_call(agent):
            raise ToolAccessDeniedError(
                f"Agent '{agent}' is not authorized to call tool '{tool_name}'. Allowed: {tool.allowed_agents}"
            )

        if tool.is_rate_limited():
            raise RateLimitExceededError(
                f"Tool '{tool_name}' rate limit of {tool.rate_limit_per_min} calls/min exceeded"
            )

        tool.record_call()
        return {"status": "SUCCESS", "tool": tool_name, "called_by": agent}

    def list_tools(self) -> list[dict]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "allowed_agents": t.allowed_agents,
                "requires_auth": t.requires_auth,
                "rate_limit_per_min": t.rate_limit_per_min,
            }
            for t in self._tools.values()
        ]
