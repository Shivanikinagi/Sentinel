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
from .incidents import IncidentMemory
from .memory import TrendEngine
from .metrics import compute_metrics
from .pipeline import build_harness
from .schemas import (
    ControllerDecision, HarnessMetrics, IncidentRecord, PolicyPackInfo, SimResponse, VehicleTrend,
)
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


class PolicyPackBody(BaseModel):
    key: str


class ShipmentBody(BaseModel):
    """Live Scenario Runner submission — an operator's shipment evaluation
    request. Thin wrapper over the same world-state + policy-engine surface
    the /simulate/* and /policy/active endpoints already expose; no new
    pipeline behaviour, just one call instead of several."""
    vehicle_id: str | None = None
    cargo_temperature: float | None = None
    ambient_temperature: float | None = None
    cooling_status: bool | None = None
    policy_pack: str | None = None
    dwell_minutes: float | None = None
    agent_a_disabled: bool = False
    agent_b_disabled: bool = False
    corrupt_critic: bool = False
    stale_signal: str | None = None


# --------------------------------------------------------------------------- core
@app.get("/health")
def health() -> dict:
    s = get_settings()
    return {"ok": True, "critic_backend": "mock" if s.use_mock_critic else "openrouter",
            "model": s.llm_model}


@app.post("/runs", response_model=ControllerDecision)
def trigger_run(policy_pack: str | None = None) -> ControllerDecision:
    return _harness.run(world_mod.get_state(), policy_pack_key=policy_pack)


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


@app.post("/simulate/shipment", response_model=SimResponse)
def sim_shipment(body: ShipmentBody) -> SimResponse:
    """Live Scenario Runner: apply an operator-submitted shipment (or a
    scenario preset the frontend expanded into one) as the world truth for
    the next run. Reuses `apply_custom` (world.py) and the existing policy
    engine — no pipeline or business-logic change."""
    if body.policy_pack:
        try:
            _harness.policy_engine.set_active(body.policy_pack)
        except KeyError:
            raise HTTPException(400, f"unknown policy pack '{body.policy_pack}'")
    world_mod.apply_custom(
        vehicle_id=body.vehicle_id,
        cargo_temperature=body.cargo_temperature,
        ambient_temperature=body.ambient_temperature,
        cooling_status=body.cooling_status,
        dwell_minutes=body.dwell_minutes,
        agent_a_disabled=body.agent_a_disabled,
        agent_b_disabled=body.agent_b_disabled,
        corrupt_critic=body.corrupt_critic,
        stale_signal=body.stale_signal,
    )
    return SimResponse(ok=True, message="shipment telemetry applied")


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


# ---------------------------------------------------------- Harness Runtime API
@app.get("/metrics", response_model=HarnessMetrics)
def get_metrics() -> HarnessMetrics:
    """Observability — Harness Runtime metrics aggregated over everything
    persisted so far: run outcomes, retries, evidence rejected, actions."""
    return compute_metrics(get_store())


@app.get("/policy/packs", response_model=list[PolicyPackInfo])
def list_policy_packs() -> list[PolicyPackInfo]:
    return _harness.policy_engine.list_packs()


@app.get("/policy/active", response_model=PolicyPackInfo)
def get_active_policy_pack() -> PolicyPackInfo:
    return _harness.policy_engine.active().info()


@app.post("/policy/active", response_model=PolicyPackInfo)
def set_active_policy_pack(body: PolicyPackBody) -> PolicyPackInfo:
    try:
        pack = _harness.policy_engine.set_active(body.key)
    except KeyError:
        raise HTTPException(400, f"unknown policy pack '{body.key}'")
    return pack.info()


@app.get("/vehicles/{vehicle_id}/trend", response_model=VehicleTrend)
def vehicle_trend(vehicle_id: str, signal: str = "cargo_temperature", limit: int = 8) -> VehicleTrend:
    return TrendEngine(get_store()).trend(vehicle_id, signal, limit=limit)


@app.get("/incidents", response_model=list[IncidentRecord])
def list_incidents(vehicle_id: str | None = None, limit: int = 20) -> list[IncidentRecord]:
    """Incident Memory — past CRITICAL_HALT runs and how they were resolved.
    Distinct from /vehicles/{id}/trend (routine signal history)."""
    return IncidentMemory(get_store()).list_incidents(vehicle_id=vehicle_id, limit=limit)


@app.get("/events/types")
def event_vocabulary() -> list[str]:
    """The fixed event vocabulary the Harness Runtime's EventBus publishes —
    the same strings that land in /audit, since Audit is one subscriber."""
    return [v for k, v in vars(AuditEvent).items() if not k.startswith("_")]


@app.get("/events/recent")
def recent_events(limit: int = 50) -> list[dict]:
    """The EventBus's own in-memory ring buffer (most-recent-first) — proof
    the bus is live, independent of what Audit persisted."""
    return [
        {"event_type": e.event_type, "run_id": e.run_id, "ts": e.ts, "payload": e.payload}
        for e in _harness.events.recent[:limit]
    ]


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


@app.post("/simulate/transient-error", response_model=SimResponse)
def sim_transient_error() -> SimResponse:
    """Demo hook for the RetryEngine: the Risk Assessment Engine's NEXT call
    fails once with a simulated network error, so the retry (and its
    "Retry #1" timeline row) can be shown recovering live."""
    backend = getattr(_harness.critic, "backend", None)
    if hasattr(backend, "trigger_transient_error"):
        backend.trigger_transient_error()
        return SimResponse(ok=True, message="Risk Assessment Engine will fail once on the next run, then retry and recover")
    return SimResponse(ok=False, message="transient-error injection only supported on the mock critic backend")


@app.post("/simulate/exhaust-retries", response_model=SimResponse)
def sim_exhaust_retries() -> SimResponse:
    """Demo hook for the 'failed safely' story: the NEXT run's Risk Assessment
    Engine fails every attempt (not just once), so the RetryEngine genuinely
    exhausts and the Controller falls back to INSUFFICIENT_DATA — no action —
    instead of guessing."""
    backend = getattr(_harness.critic, "backend", None)
    if hasattr(backend, "trigger_exhaust_retries_demo"):
        backend.trigger_exhaust_retries_demo(get_settings().critic_max_attempts)
        return SimResponse(ok=True, message="Risk Assessment Engine will fail every attempt on the next run — retries will exhaust into INSUFFICIENT_DATA")
    return SimResponse(ok=False, message="exhaust-retries injection only supported on the mock critic backend")


@app.post("/simulate/verifier-feedback", response_model=SimResponse)
def sim_verifier_feedback() -> SimResponse:
    """Demo hook for the Verifier -> Risk Assessment Engine feedback loop: the
    NEXT run's first assessment will include one ungrounded risk factor, so
    the Verifier rejects it, feeds its reason back, and the Critic's revised
    (and re-verified) answer can be shown recovering live."""
    backend = getattr(_harness.critic, "backend", None)
    if hasattr(backend, "trigger_verifier_feedback_demo"):
        backend.trigger_verifier_feedback_demo()
        return SimResponse(ok=True, message="Risk Assessment Engine will emit an ungrounded factor once — Verifier feedback loop will engage on the next run")
    return SimResponse(ok=False, message="verifier-feedback injection only supported on the mock critic backend")


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

