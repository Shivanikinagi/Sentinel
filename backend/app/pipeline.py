"""Harness Runtime — the shell every other layer plugs into.

  Planner -> Supervisor(agents -> gate -> correlation -> risk assessment engine
             (retry + circuit breaker) -> verifier -> deterministic controller)
  -> Harness (persists evidence + decision, requests an action on CRITICAL_HALT,
     writes the audit boundary events) -> Store / Action Gateway / Audit

`Harness` is kept as the public entry point (`build_harness().run(world)`) for
full backward compatibility with the existing test suite; internally it now
owns a `Supervisor` (agents/gate/critic/verifier/controller), a `Planner`
(agent scheduling), a `RetryEngine` (bounded retry around the Risk Assessment
Engine call), and a `PolicyEngine` (pluggable policy packs — see
policy_packs.py) instead of doing all of that inline.
"""
from __future__ import annotations

from uuid import uuid4

from .actions import ActionGateway
from .agents import EnvironmentObserver, VehicleObserver
from .audit import Audit, AuditEvent
from .circuit_breaker import get_circuit_breaker
from .confidence import compute_composite
from .config import Settings, get_settings
from .correlation import CorrelationEngine
from .critic import Critic, build_critic
from .events import EventBus, audit_sink
from .memory import TrendEngine
from .planner import Planner
from .policy_packs import PolicyEngine, PolicyPack
from .retry_engine import RetryEngine
from .run_state import RunState
from .schemas import ActionType, ControllerDecision, ControllerState, DecisionTrace
from .store import Store, get_store
from .supervisor import Supervisor
from .tools import ToolRegistry
from .verifier import Verifier
from .world import WorldState


class Harness:
    def __init__(self, store: Store, audit: Audit, gateway: ActionGateway,
                 critic: Critic, settings: Settings,
                 policy_engine: PolicyEngine | None = None,
                 events: EventBus | None = None) -> None:
        self._store = store
        self._audit = audit
        self._gateway = gateway
        self._critic = critic
        self._settings = settings
        self._policy_engine = policy_engine or PolicyEngine(settings.active_policy_pack)
        self._circuit_breaker = get_circuit_breaker()
        self._memory = TrendEngine(store)

        # One Event Bus for the whole runtime. Audit subscribes to it (see
        # build_harness) so every stage's event lands in the audit table
        # exactly as before — the bus is a decoupling, not a behavior change.
        self._events = events or EventBus()
        self._events.subscribe(audit_sink(audit))

        self._supervisor = Supervisor(
            critic=critic, settings=settings,
            agent_a=VehicleObserver(), agent_b=EnvironmentObserver(),
            planner=Planner(), correlation_engine=CorrelationEngine(),
            verifier=Verifier(), tool_registry=ToolRegistry(),
            circuit_breaker=self._circuit_breaker,
            retry_engine=RetryEngine(max_attempts=settings.critic_max_attempts),
            events=self._events,
        )

    def run(self, world: WorldState, vehicle_id: str | None = None,
            policy_pack_key: str | None = None) -> ControllerDecision:
        run_id = f"run_{uuid4().hex[:12]}"
        vehicle_id = vehicle_id or world.vehicle.vehicle_id
        pack: PolicyPack = self._policy_engine.get(policy_pack_key)

        self._events.publish(AuditEvent.RUN_STARTED, run_id,
                             {"scenario": world.scenario, "vehicle_id": vehicle_id, "policy_pack": pack.key})

        run_state: RunState = self._supervisor.execute(world, run_id, vehicle_id, pack)

        self._store.insert_evidence(
            [e.model_dump(mode="json") for e in run_state.observed_evidence]
        )

        escalation_id = None
        if run_state.request_action:
            ar = self._gateway.request(
                run_id=run_id, vehicle_id=vehicle_id,
                action_type=ActionType.HALT_AUTOMATION, reason=run_state.decision_reason or "",
                context={
                    "risk_level": run_state.risk_matrix.risk_level.value if run_state.risk_matrix else "HIGH",
                    "risk_factors": (run_state.risk_matrix.risk_factors if run_state.risk_matrix
                                    else run_state.correlation_conflicts),
                    "confidence": run_state.confidence,
                },
            )
            escalation_id = ar.action_id

        # Composite confidence needs Store (historical reliability), which is
        # why it's computed here rather than inside the Supervisor.
        historical_reliability = self._memory.reliability_score(vehicle_id, exclude_run_id=run_id)
        composite = compute_composite(
            evidence_quality=run_state.confidence,
            verifier_valid=bool(run_state.verifier_result and run_state.verifier_result.valid),
            trusted_count=len(run_state.trusted_evidence),
            excluded_count=len(run_state.excluded_evidence),
            conflict_count=len(run_state.correlation_conflicts),
            historical_reliability=historical_reliability,
        )

        decision = ControllerDecision(
            run_id=run_id, vehicle_id=vehicle_id,
            controller_state=run_state.controller_state or ControllerState.INSUFFICIENT_DATA,
            reason=run_state.decision_reason or "",
            confidence=run_state.confidence,
            confidence_breakdown=run_state.confidence_breakdown,
            composite_confidence=composite,
            policy_pack=pack.key,
            risk_matrix=run_state.risk_matrix,
            critic_rejected=run_state.critic_rejected,
            trace=DecisionTrace(
                evidence_ids=[e.evidence_id for e in run_state.all_evidence],
                evidence_snapshot=run_state.all_evidence,
                excluded_evidence_ids=run_state.excluded_evidence_ids,
                gate_notes=run_state.gate_notes,
                gate_stage_results=run_state.gate_stage_results,
                agents_reporting=run_state.agents_reporting,
                agents_unavailable=run_state.agents_unavailable,
                correlation_conflicts=run_state.correlation_conflicts,
                verifier_result=run_state.verifier_result,
                circuit_breaker_open=run_state.circuit_breaker_open,
                decision_chain=run_state.trace,
                retries=run_state.retries,
                feedback_loop_triggered=run_state.feedback_loop_triggered,
                feedback_loop_reason=run_state.feedback_loop_reason,
            ),
            escalation_id=escalation_id,
        )

        self._store.upsert_decision(decision.model_dump(mode="json"))
        self._events.publish(AuditEvent.DECISION_MADE, run_id, {
            "controller_state": decision.controller_state.value,
            "confidence": decision.confidence, "reason": decision.reason,
            "escalation_id": escalation_id,
        })
        self._events.publish(AuditEvent.RUN_COMPLETED, run_id, {
            "controller_state": decision.controller_state.value,
        })

        return decision

    @property
    def gateway(self) -> ActionGateway:
        return self._gateway

    @property
    def store(self) -> Store:
        return self._store

    @property
    def critic(self) -> Critic:
        return self._critic

    @property
    def tool_registry(self) -> ToolRegistry:
        return self._supervisor.tool_registry

    @property
    def circuit_breaker(self):
        return self._circuit_breaker

    @property
    def policy_engine(self) -> PolicyEngine:
        return self._policy_engine

    @property
    def events(self) -> EventBus:
        return self._events


def build_harness(store: Store | None = None,
                  settings: Settings | None = None) -> Harness:
    settings = settings or get_settings()
    store = store or get_store()
    audit = Audit(store)
    gateway = ActionGateway(store, audit, settings=settings)
    policy_engine = PolicyEngine(settings.active_policy_pack)
    critic = build_critic(settings, pack=policy_engine.active())
    return Harness(store=store, audit=audit, gateway=gateway, critic=critic,
                   settings=settings, policy_engine=policy_engine)
