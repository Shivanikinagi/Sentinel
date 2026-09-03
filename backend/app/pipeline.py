"""Orchestrator — ties the five layers into one deterministic run.

  observe (agents) -> gate (evidence) -> critic (intelligence) ->
  controller (decision) -> gateway (authority) -> persist + audit

Everything is synchronous and easy to follow. The Controller is the only path to
the gateway, and only fires it on CRITICAL_HALT.
"""
from __future__ import annotations

from uuid import uuid4

from . import controller, gate
from .actions import ActionGateway
from .agents import AgentUnavailable, EnvironmentObserver, VehicleObserver
from .audit import Audit, AuditEvent
from .config import Settings, get_settings
from .critic import Critic, build_critic
from .schemas import (
    ActionType, AgentSource, ControllerDecision, ControllerState, DecisionTrace,
    Evidence,
)
from .store import Store, get_store
from .world import WorldState


class Harness:
    def __init__(self, store: Store, audit: Audit, gateway: ActionGateway,
                 critic: Critic, settings: Settings) -> None:
        self._store = store
        self._audit = audit
        self._gateway = gateway
        self._critic = critic
        self._settings = settings
        # Observers are stateless and hold no reference to gateway/critic.
        self._agent_a = VehicleObserver()
        self._agent_b = EnvironmentObserver()

    def run(self, world: WorldState, vehicle_id: str | None = None) -> ControllerDecision:
        run_id = f"run_{uuid4().hex[:12]}"
        vehicle_id = vehicle_id or world.vehicle.vehicle_id
        self._audit.record(AuditEvent.RUN_STARTED,
                           {"scenario": world.scenario, "vehicle_id": vehicle_id},
                           run_id=run_id)

        evidence, unavailable = self._observe(world, run_id, vehicle_id)
        self._store.insert_evidence([e.model_dump(mode="json") for e in evidence])
        self._audit.record(
            AuditEvent.EVIDENCE_OBSERVED,
            {"count": len(evidence), "signals": [e.signal for e in evidence]},
            run_id=run_id,
        )

        gate_result = gate.evaluate(evidence, unavailable, settings=self._settings)
        self._audit.record(AuditEvent.GATE_EVALUATED, {
            "trusted": [e.signal for e in gate_result.trusted],
            "excluded_ids": gate_result.excluded_ids,
            "missing_required": gate_result.missing_required,
            "notes": gate_result.gate_notes,
        }, run_id=run_id)

        # corrupt_critic is a one-shot demo switch — consume it.
        corrupt = world.corrupt_critic
        if corrupt:
            world.corrupt_critic = False
        critic_result = self._critic.assess(gate_result.trusted, corrupt=corrupt)
        if critic_result.rejected:
            self._audit.record(AuditEvent.CRITIC_REJECTED,
                               {"reason": critic_result.rejection_reason,
                                "raw": critic_result.raw}, run_id=run_id)
        else:
            self._audit.record(AuditEvent.CRITIC_ASSESSED,
                               critic_result.matrix.model_dump(mode="json"),
                               run_id=run_id)

        outcome = controller.decide(gate_result, critic_result)

        escalation_id = None
        if outcome.request_action:
            ar = self._gateway.request(
                run_id=run_id, vehicle_id=vehicle_id,
                action_type=ActionType.HALT_AUTOMATION, reason=outcome.reason,
                context={
                    "risk_level": critic_result.matrix.risk_level.value,
                    "risk_factors": critic_result.matrix.risk_factors,
                    "confidence": outcome.confidence,
                },
            )
            escalation_id = ar.action_id

        decision = ControllerDecision(
            run_id=run_id, vehicle_id=vehicle_id,
            controller_state=outcome.state, reason=outcome.reason,
            confidence=outcome.confidence, risk_matrix=critic_result.matrix,
            critic_rejected=critic_result.rejected,
            trace=DecisionTrace(
                evidence_ids=[e.evidence_id for e in gate_result.all_evidence],
                evidence_snapshot=gate_result.all_evidence,
                excluded_evidence_ids=gate_result.excluded_ids,
                gate_notes=gate_result.gate_notes,
                agents_reporting=gate_result.agents_reporting,
                agents_unavailable=gate_result.agents_unavailable,
            ),
            escalation_id=escalation_id,
        )
        self._store.upsert_decision(decision.model_dump(mode="json"))
        self._audit.record(AuditEvent.DECISION_MADE, {
            "controller_state": decision.controller_state.value,
            "confidence": decision.confidence, "reason": decision.reason,
            "escalation_id": escalation_id,
        }, run_id=run_id)
        return decision

    def _observe(self, world: WorldState, run_id: str, vehicle_id: str
                 ) -> tuple[list[Evidence], list[AgentSource]]:
        evidence: list[Evidence] = []
        unavailable: list[AgentSource] = []
        for agent, source in ((self._agent_a, AgentSource.AGENT_A),
                              (self._agent_b, AgentSource.AGENT_B)):
            try:
                evidence.extend(agent.observe(world, run_id, vehicle_id))
            except AgentUnavailable:
                unavailable.append(source)
                self._audit.record(AuditEvent.AGENT_UNAVAILABLE,
                                   {"agent": source.value}, run_id=run_id)
        return evidence, unavailable

    # convenience read-throughs
    @property
    def gateway(self) -> ActionGateway:
        return self._gateway

    @property
    def store(self) -> Store:
        return self._store


def build_harness(store: Store | None = None,
                  settings: Settings | None = None) -> Harness:
    settings = settings or get_settings()
    store = store or get_store()
    audit = Audit(store)
    gateway = ActionGateway(store, audit, settings)
    critic = build_critic(settings)
    return Harness(store, audit, gateway, critic, settings)
