"""Orchestrator — ties the five layers into one deterministic run with enterprise verification.

  observe (agents + tools) -> gate (evidence) -> correlation (conflicts) ->
  circuit_breaker + critic (intelligence) -> verifier (validation) ->
  controller (decision) -> gateway (authority) -> persist + audit
"""
from __future__ import annotations

import time
from uuid import uuid4

from . import controller, gate
from .actions import ActionGateway
from .agents import AgentUnavailable, EnvironmentObserver, VehicleObserver
from .audit import Audit, AuditEvent
from .circuit_breaker import CircuitOpenError, get_circuit_breaker
from .config import Settings, get_settings
from .correlation import CorrelationEngine
from .critic import Critic, CriticResult, build_critic
from .schemas import (
    ActionType, AgentSource, ControllerDecision, ControllerState, DecisionStep,
    DecisionTrace, Evidence, VerifierResult,
)
from .store import Store, get_store
from .tools import ToolRegistry
from .verifier import Verifier
from .world import WorldState


class Harness:
    def __init__(self, store: Store, audit: Audit, gateway: ActionGateway,
                 critic: Critic, settings: Settings) -> None:
        self._store = store
        self._audit = audit
        self._gateway = gateway
        self._critic = critic
        self._settings = settings
        self._agent_a = VehicleObserver()
        self._agent_b = EnvironmentObserver()
        self._correlation_engine = CorrelationEngine()
        self._verifier = Verifier()
        self._tool_registry = ToolRegistry()
        self._circuit_breaker = get_circuit_breaker()

    def run(self, world: WorldState, vehicle_id: str | None = None) -> ControllerDecision:
        run_id = f"run_{uuid4().hex[:12]}"
        vehicle_id = vehicle_id or world.vehicle.vehicle_id
        decision_chain: list[DecisionStep] = []

        self._audit.record(
            AuditEvent.RUN_STARTED,
            {"scenario": world.scenario, "vehicle_id": vehicle_id},
            run_id=run_id,
        )

        # Step 1: Telemetry Observation
        t0 = time.perf_counter()
        evidence, unavailable = self._observe(world, run_id, vehicle_id)
        self._store.insert_evidence([e.model_dump(mode="json") for e in evidence])
        dur_obs = (time.perf_counter() - t0) * 1000
        decision_chain.append(DecisionStep(
            step_name="telemetry_observation",
            status="WARNING" if unavailable else "OK",
            detail=f"{len(evidence)} signals collected, {len(unavailable)} agents unavailable",
            duration_ms=round(dur_obs, 2),
        ))

        self._audit.record(
            AuditEvent.EVIDENCE_OBSERVED,
            {"count": len(evidence), "signals": [e.signal for e in evidence]},
            run_id=run_id,
        )

        # Step 2: Trust Gate Evaluation
        t0 = time.perf_counter()
        gate_result = gate.evaluate(evidence, unavailable, settings=self._settings)
        dur_gate = (time.perf_counter() - t0) * 1000
        gate_status = "WARNING" if gate_result.excluded_ids or gate_result.missing_required else "OK"
        decision_chain.append(DecisionStep(
            step_name="trust_gate",
            status=gate_status,
            detail=f"{len(gate_result.trusted)} trusted, {len(gate_result.excluded_ids)} excluded",
            duration_ms=round(dur_gate, 2),
        ))

        self._audit.record(AuditEvent.GATE_EVALUATED, {
            "trusted": [e.signal for e in gate_result.trusted],
            "excluded_ids": gate_result.excluded_ids,
            "missing_required": gate_result.missing_required,
            "notes": gate_result.gate_notes,
        }, run_id=run_id)

        # Step 3: Evidence Correlation Engine
        t0 = time.perf_counter()
        correlation = self._correlation_engine.correlate(gate_result.trusted)
        dur_corr = (time.perf_counter() - t0) * 1000
        decision_chain.append(DecisionStep(
            step_name="evidence_correlation",
            status="WARNING" if correlation.has_conflicts else "OK",
            detail=f"{len(correlation.conflicts)} physical conflicts detected",
            duration_ms=round(dur_corr, 2),
        ))

        # Step 4: Consensus Critic (with Circuit Breaker)
        t0 = time.perf_counter()
        corrupt = world.corrupt_critic
        if corrupt:
            world.corrupt_critic = False

        critic_result: CriticResult
        circuit_open = self._circuit_breaker.is_open()
        try:
            critic_result = self._circuit_breaker.execute(
                lambda: self._critic.assess(gate_result.trusted, corrupt=corrupt)
            )
        except CircuitOpenError as exc:
            critic_result = CriticResult(
                matrix=None,
                rejected=True,
                backend="circuit_breaker_open",
                rejection_reason=str(exc),
            )
            circuit_open = True

        dur_critic = (time.perf_counter() - t0) * 1000
        decision_chain.append(DecisionStep(
            step_name="consensus_critic",
            status="FAILED" if critic_result.rejected else "OK",
            detail=f"Backend: {critic_result.backend}, Rejected: {critic_result.rejected}",
            duration_ms=round(dur_critic, 2),
        ))

        if critic_result.rejected:
            self._audit.record(
                AuditEvent.CRITIC_REJECTED,
                {"reason": critic_result.rejection_reason, "raw": critic_result.raw},
                run_id=run_id,
            )
        else:
            self._audit.record(
                AuditEvent.CRITIC_ASSESSED,
                critic_result.matrix.model_dump(mode="json"),
                run_id=run_id,
            )

        # Step 5: Verifier Sub-System
        t0 = time.perf_counter()
        verifier_result: VerifierResult
        if not critic_result.rejected and critic_result.matrix is not None:
            verifier_result = self._verifier.verify(critic_result.matrix, gate_result.trusted)
            if not verifier_result.valid:
                critic_result.rejected = True
                critic_result.rejection_reason = f"verifier_check_failed: {verifier_result.reason}"
        else:
            verifier_result = VerifierResult(
                valid=False,
                reason="Critic output was rejected prior to verification",
                checks_failed=["pre_verification_critic_rejection"],
            )

        dur_verif = (time.perf_counter() - t0) * 1000
        decision_chain.append(DecisionStep(
            step_name="verifier_subsystem",
            status="OK" if verifier_result.valid else "FAILED",
            detail=verifier_result.reason or "Verification evaluated",
            duration_ms=round(dur_verif, 2),
        ))

        # Step 6: Deterministic Controller
        t0 = time.perf_counter()
        outcome = controller.decide(gate_result, critic_result)
        dur_ctrl = (time.perf_counter() - t0) * 1000
        decision_chain.append(DecisionStep(
            step_name="deterministic_controller",
            status="OK" if outcome.state == ControllerState.AUTO_OPTIMIZE else "WARNING" if outcome.state == ControllerState.INSUFFICIENT_DATA else "FAILED",
            detail=f"State: {outcome.state.value}, Confidence: {int(outcome.confidence * 100)}%",
            duration_ms=round(dur_ctrl, 2),
        ))

        # Step 7: Action Gateway
        escalation_id = None
        if outcome.request_action:
            ar = self._gateway.request(
                run_id=run_id, vehicle_id=vehicle_id,
                action_type=ActionType.HALT_AUTOMATION, reason=outcome.reason,
                context={
                    "risk_level": critic_result.matrix.risk_level.value if critic_result.matrix else "HIGH",
                    "risk_factors": critic_result.matrix.risk_factors if critic_result.matrix else correlation.conflicts,
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
                correlation_conflicts=correlation.conflicts,
                verifier_result=verifier_result,
                circuit_breaker_open=circuit_open,
                decision_chain=decision_chain,
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

        # Execute observer tools via ToolRegistry for audited execution
        try:
            self._tool_registry.execute_tool("agent_a", "get_cargo_telemetry")
        except Exception:
            pass

        try:
            self._tool_registry.execute_tool("agent_b", "get_environmental_telemetry")
        except Exception:
            pass

        for agent, source in ((self._agent_a, AgentSource.AGENT_A),
                              (self._agent_b, AgentSource.AGENT_B)):
            try:
                evidence.extend(agent.observe(world, run_id, vehicle_id))
            except AgentUnavailable:
                unavailable.append(source)
                self._audit.record(AuditEvent.AGENT_UNAVAILABLE,
                                   {"agent": source.value}, run_id=run_id)
        return evidence, unavailable

    @property
    def gateway(self) -> ActionGateway:
        return self._gateway

    @property
    def store(self) -> Store:
        return self._store

    @property
    def tool_registry(self) -> ToolRegistry:
        return self._tool_registry

    @property
    def circuit_breaker(self):
        return self._circuit_breaker


def build_harness(store: Store | None = None,
                  settings: Settings | None = None) -> Harness:
    settings = settings or get_settings()
    store = store or get_store()
    audit = Audit(store)
    gateway = ActionGateway(store, audit, settings=settings)
    critic = build_critic(settings)
    return Harness(store=store, audit=audit, gateway=gateway, critic=critic, settings=settings)
