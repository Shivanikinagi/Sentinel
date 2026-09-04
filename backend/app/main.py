"""FastAPI surface for Fleet-Harness.

Thin HTTP layer over the pipeline: every demo scene is reachable via an endpoint,
no code edits required. The frontend polls /state + /decisions to stay live.
"""
from __future__ import annotations

from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import world as world_mod
from .actions import ActionError
from .audit import Audit, AuditEvent
from .config import get_settings
from .pipeline import build_harness
from .schemas import ControllerDecision, SimResponse
from .security import probe_unauthorized_action
from .store import get_store

app = FastAPI(title="Fleet-Harness", version="1.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

# One process-wide harness bound to the shared store. The mocked world is a
# separate global that the /simulate endpoints mutate.
_harness = build_harness()


# ------------------------------------------------------------------ request models
class KillAgentBody(BaseModel):
    agent: Literal["agent_a", "agent_b"]
    disabled: bool = True


class ScenarioBody(BaseModel):
    name: str


class StaleSignalBody(BaseModel):
    signal: str | None = None


class ApproveBody(BaseModel):
    approver: str


class RejectBody(BaseModel):
    approver: str
    reason: str


# --------------------------------------------------------------------------- core
@app.get("/health")
def health() -> dict:
    s = get_settings()
    return {"ok": True, "critic_backend": "mock" if s.use_mock_critic else "openrouter",
            "model": s.llm_model}


@app.post("/runs", response_model=ControllerDecision)
def trigger_run() -> ControllerDecision:
    return _harness.run(world_mod.get_state())


@app.get("/decisions", response_model=list[ControllerDecision])
def recent_decisions(limit: int = 20) -> list[ControllerDecision]:
    return [ControllerDecision.model_validate(d)
            for d in get_store().list_recent_decisions(limit)]


@app.get("/decisions/{run_id}", response_model=ControllerDecision)
def get_decision(run_id: str) -> ControllerDecision:
    d = get_store().get_decision(run_id)
    if not d:
        raise HTTPException(404, f"run {run_id} not found")
    return ControllerDecision.model_validate(d)


@app.get("/state")
def get_world_state() -> dict:
    """Raw sim truth + demo switches. Lets the dashboard show truth vs. evidence."""
    w = world_mod.get_state()
    return {
        "scenario": w.scenario,
        "vehicle": vars(w.vehicle),
        "environment": vars(w.environment),
        "switches": {
            "agent_a_disabled": w.agent_a_disabled,
            "agent_b_disabled": w.agent_b_disabled,
            "corrupt_critic": w.corrupt_critic,
            "force_stale_signal": w.force_stale_signal,
        },
    }


@app.get("/audit")
def get_audit(limit: int = 50) -> list[dict]:
    return get_store().recent_audit(limit)


# ------------------------------------------------------------- Action Gateway (L2)
@app.get("/actions/pending")
def pending_actions() -> list[dict]:
    return [a.model_dump(mode="json") for a in _harness.gateway.pending()]


@app.get("/actions/{action_id}")
def get_action(action_id: str) -> dict:
    ar = _harness.gateway.get(action_id)
    if not ar:
        raise HTTPException(404, f"action {action_id} not found")
    return {"action": ar.model_dump(mode="json"),
            "events": _harness.gateway.events(action_id)}


@app.post("/actions/{action_id}/approve")
def approve_action(action_id: str, body: ApproveBody) -> dict:
    if _harness.gateway.get(action_id) is None:
        raise HTTPException(404, f"action {action_id} not found")
    try:
        ar = _harness.gateway.approve(action_id, approver=body.approver)
    except ActionError as e:
        raise HTTPException(409, str(e))
    return ar.model_dump(mode="json")


@app.post("/actions/{action_id}/reject")
def reject_action(action_id: str, body: RejectBody) -> dict:
    if _harness.gateway.get(action_id) is None:
        raise HTTPException(404, f"action {action_id} not found")
    try:
        ar = _harness.gateway.reject(action_id, approver=body.approver,
                                     reason=body.reason)
    except ActionError as e:
        raise HTTPException(409, str(e))
    return ar.model_dump(mode="json")


# ----------------------------------------------------------------- demo triggers
@app.post("/simulate/scenario", response_model=SimResponse)
def sim_scenario(body: ScenarioBody) -> SimResponse:
    try:
        world_mod.apply_scenario(body.name)
    except KeyError:
        raise HTTPException(400, f"unknown scenario '{body.name}'. "
                                 f"known: {list(world_mod.SCENARIOS)}")
    return SimResponse(ok=True, message=f"scenario set to {body.name}")


@app.post("/simulate/kill-agent", response_model=SimResponse)
def sim_kill_agent(body: KillAgentBody) -> SimResponse:
    w = world_mod.get_state()
    if body.agent == "agent_a":
        w.agent_a_disabled = body.disabled
    else:
        w.agent_b_disabled = body.disabled
    verb = "disabled" if body.disabled else "restored"
    return SimResponse(ok=True, message=f"{body.agent} {verb}")


@app.post("/simulate/corrupt-llm", response_model=SimResponse)
def sim_corrupt_llm() -> SimResponse:
    world_mod.get_state().corrupt_critic = True
    return SimResponse(ok=True, message="critic will emit malformed output on next run")


@app.post("/simulate/stale-signal", response_model=SimResponse)
def sim_stale_signal(body: StaleSignalBody) -> SimResponse:
    world_mod.get_state().force_stale_signal = body.signal
    msg = f"signal '{body.signal}' will be backdated" if body.signal \
        else "stale-signal cleared"
    return SimResponse(ok=True, message=msg)


@app.post("/simulate/reset", response_model=SimResponse)
def sim_reset() -> SimResponse:
    world_mod.reset()
    get_store().reset()
    return SimResponse(ok=True, message="world and store reset to healthy")


@app.get("/tools")
def list_tools() -> list[dict]:
    return _harness.tool_registry.list_tools()


@app.post("/simulate/sensor-drift", response_model=SimResponse)
def sim_sensor_drift(cargo_temp: float = 14.5) -> SimResponse:
    w = world_mod.get_state()
    w.vehicle.cargo_temperature = cargo_temp
    return SimResponse(ok=True, message=f"sensor drift injected: cargo_temperature set to {cargo_temp}°C")


@app.post("/simulate/circuit-breaker", response_model=SimResponse)
def sim_circuit_breaker() -> SimResponse:
    _harness.circuit_breaker.record_failure()
    _harness.circuit_breaker.record_failure()
    _harness.circuit_breaker.record_failure()
    return SimResponse(ok=True, message="LLM Circuit Breaker tripped to OPEN state (3 failures recorded)")


@app.post("/simulate/emergency-override", response_model=SimResponse)
def sim_emergency_override() -> SimResponse:
    w = world_mod.get_state()
    w.scenario = "compound_risk"
    w.vehicle.cargo_temperature = 15.0
    w.vehicle.cooling_status = 1.0
    return SimResponse(ok=True, message="EMERGENCY HUMAN OVERRIDE ENGAGED: Halting automation immediately")



@app.post("/simulate/unauthorized-action")
def sim_unauthorized_action() -> dict:
    """Red-team probe: prove an agent has no callable path to an action."""
    result = probe_unauthorized_action()
    Audit(get_store()).record(AuditEvent.SECURITY_PROBE, result)
    return result


@app.post("/simulate/unauthorized-tool")
def sim_unauthorized_tool() -> dict:
    """Red-team probe: prove Agent A cannot call Agent B tools."""
    try:
        _harness.tool_registry.execute_tool("agent_a", "get_environmental_telemetry")
        return {"blocked": False, "detail": "Agent A called Agent B tool!"}
    except Exception as exc:
        return {
            "blocked": True,
            "vector": "agent_a_calling_agent_b_tool",
            "outcome": "blocked",
            "detail": str(exc),
        }

