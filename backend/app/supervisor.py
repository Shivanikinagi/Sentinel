"""Supervisor — starts agents, monitors execution, retries transient failures,
collects evidence, and produces the execution trace. This is what the rest of
the Harness Runtime (Store, Audit, Action Gateway) plugs results INTO.

`Supervisor.execute()` owns exactly the Intelligence -> Evidence -> Policy ->
Decision layers (agents through the deterministic Controller); it never touches
Store or the Action Gateway — persistence and authority stay the Harness's job,
mirroring the same isolation the codebase already proves for agents/critic. It
reads and writes ONE `RunState` per run instead of threading a chain of local
variables from stage to stage, which is what makes this a Supervisor over a
harness rather than a plain pipeline function.
"""
from __future__ import annotations

import time

from . import controller
from .agents import AgentUnavailable, EnvironmentObserver, VehicleObserver
from .audit import Audit, AuditEvent
from .circuit_breaker import CircuitBreaker, CircuitOpenError
from .config import Settings
from .correlation import CorrelationEngine
from .critic import Critic, CriticResult
from .gate import evaluate as gate_evaluate
from .planner import Planner
from .policy_packs import PolicyPack
from .retry_engine import RetryEngine
from .run_state import RunState
from .schemas import AgentSource, ControllerState, DecisionStep, VerifierResult
from .tools import ToolRegistry
from .verifier import Verifier
from .world import WorldState


class Supervisor:
    def __init__(
        self, *, critic: Critic, settings: Settings,
        agent_a: VehicleObserver | None = None,
        agent_b: EnvironmentObserver | None = None,
        planner: Planner | None = None,
        correlation_engine: CorrelationEngine | None = None,
        verifier: Verifier | None = None,
        tool_registry: ToolRegistry | None = None,
        circuit_breaker: CircuitBreaker | None = None,
        retry_engine: RetryEngine | None = None,
        audit: Audit | None = None,
    ) -> None:
        self._critic = critic
        self._settings = settings
        self._agent_a = agent_a or VehicleObserver()
        self._agent_b = agent_b or EnvironmentObserver()
        self._planner = planner or Planner()
        self._correlation_engine = correlation_engine or CorrelationEngine()
        self._verifier = verifier or Verifier()
        self._tool_registry = tool_registry or ToolRegistry()
        self._circuit_breaker = circuit_breaker
        self._retry_engine = retry_engine or RetryEngine(
            max_attempts=getattr(settings, "critic_max_attempts", 2)
        )
        self._audit = audit

    @property
    def tool_registry(self) -> ToolRegistry:
        return self._tool_registry

    def execute(self, world: WorldState, run_id: str, vehicle_id: str,
                policy_pack: PolicyPack) -> RunState:
        run_state = RunState(run_id=run_id, vehicle_id=vehicle_id, policy_pack=policy_pack.key)

        self._observe(world, run_state)
        self._gate(world, run_state, policy_pack)
        self._correlate(run_state, policy_pack)
        self._assess(world, run_state, policy_pack)
        self._verify(run_state)
        self._decide(run_state, policy_pack)

        run_state.status = run_state.status  # left RUNNING; Harness marks COMPLETED
        return run_state

    # -- Stage 1: Telemetry Observation (Planner + agents + ToolRegistry) -------
    def _observe(self, world: WorldState, run_state: RunState) -> None:
        t0 = time.perf_counter()
        plan = self._planner.plan(self._agent_a, self._agent_b)

        tool_by_source = {
            AgentSource.AGENT_A: ("agent_a", "get_cargo_telemetry"),
            AgentSource.AGENT_B: ("agent_b", "get_environmental_telemetry"),
        }

        for planned in plan.agents:
            agent_name, tool_name = tool_by_source[planned.source]
            try:
                self._tool_registry.execute_tool(agent_name, tool_name)
            except Exception:
                pass  # tool call is an audited side-channel only, never fatal

            try:
                evidence = planned.agent.observe(world, run_state.run_id, run_state.vehicle_id)
                run_state.observed_evidence.extend(evidence)
                run_state.completed_agents.append(planned.name)
            except AgentUnavailable:
                run_state.agents_unavailable.append(planned.source)
                run_state.failed_agents.append(planned.name)
                if self._audit:
                    self._audit.record(AuditEvent.AGENT_UNAVAILABLE,
                                       {"agent": planned.source.value}, run_id=run_state.run_id)

        dur = (time.perf_counter() - t0) * 1000
        run_state.record_step(DecisionStep(
            step_name="telemetry_observation",
            status="WARNING" if run_state.agents_unavailable else "OK",
            detail=(f"{len(run_state.observed_evidence)} signals collected via "
                   f"{plan.rationale}, {len(run_state.agents_unavailable)} agents unavailable"),
            duration_ms=round(dur, 2),
        ))
        if self._audit:
            self._audit.record(AuditEvent.EVIDENCE_OBSERVED, {
                "count": len(run_state.observed_evidence),
                "signals": [e.signal for e in run_state.observed_evidence],
            }, run_id=run_state.run_id)

    # -- Stage 2: Trust Gate (4 sub-stages, see gate.py) -------------------------
    def _gate(self, world: WorldState, run_state: RunState, policy_pack: PolicyPack) -> None:
        t0 = time.perf_counter()
        result = gate_evaluate(run_state.observed_evidence, run_state.agents_unavailable,
                               settings=self._settings, policy_pack=policy_pack)
        dur = (time.perf_counter() - t0) * 1000

        run_state.trusted_evidence = result.trusted
        run_state.excluded_evidence = result.excluded
        run_state.excluded_evidence_ids = result.excluded_ids
        run_state.gate_notes = result.gate_notes
        run_state.gate_stage_results = result.stage_results
        run_state.missing_required = result.missing_required
        run_state.agents_reporting = result.agents_reporting

        status = "WARNING" if result.excluded_ids or result.missing_required else "OK"
        run_state.record_step(DecisionStep(
            step_name="trust_gate", status=status,
            detail=f"{len(result.trusted)} trusted, {len(result.excluded_ids)} excluded",
            duration_ms=round(dur, 2),
        ))
        if self._audit:
            self._audit.record(AuditEvent.GATE_EVALUATED, {
                "trusted": [e.signal for e in result.trusted],
                "excluded_ids": result.excluded_ids,
                "missing_required": result.missing_required,
                "notes": result.gate_notes,
            }, run_id=run_state.run_id)

    # -- Stage 3: Evidence Correlation -------------------------------------------
    def _correlate(self, run_state: RunState, policy_pack: PolicyPack) -> None:
        t0 = time.perf_counter()
        correlation = self._correlation_engine.correlate(
            run_state.trusted_evidence, rules=policy_pack.correlation_rules
        )
        dur = (time.perf_counter() - t0) * 1000
        run_state.correlation_conflicts = correlation.conflicts
        run_state.record_step(DecisionStep(
            step_name="evidence_correlation",
            status="WARNING" if correlation.has_conflicts else "OK",
            detail=f"{len(correlation.conflicts)} physical conflicts detected",
            duration_ms=round(dur, 2),
        ))

    # -- Stage 4: Risk Assessment Engine (Critic), with retry + circuit breaker -
    def _assess(self, world: WorldState, run_state: RunState, policy_pack: PolicyPack) -> None:
        t0 = time.perf_counter()
        corrupt = world.corrupt_critic
        if corrupt:
            world.corrupt_critic = False

        backend = getattr(self._critic, "backend", None)
        if hasattr(backend, "set_pack"):
            backend.set_pack(policy_pack)

        circuit_open = self._circuit_breaker.is_open() if self._circuit_breaker else False
        critic_result: CriticResult
        attempt = 1
        max_attempts = self._retry_engine.max_attempts

        while True:
            try:
                call = lambda: self._critic.assess(run_state.trusted_evidence, corrupt=corrupt)
                critic_result = self._circuit_breaker.execute(call) if self._circuit_breaker else call()
            except CircuitOpenError as exc:
                critic_result = CriticResult(matrix=None, rejected=True,
                                             backend="circuit_breaker_open",
                                             rejection_reason=str(exc))
                circuit_open = True
                break

            transient = bool(critic_result.rejected and critic_result.rejection_reason
                            and critic_result.rejection_reason.startswith("backend_error"))
            if not transient or attempt >= max_attempts:
                break

            retry_step = DecisionStep(
                step_name=f"retry_risk_assessment_engine",
                status="WARNING",
                detail=f"Attempt {attempt} failed ({critic_result.rejection_reason}); retrying…",
                duration_ms=0.0,
            )
            run_state.record_retry(retry_step)
            if self._audit:
                self._audit.record(AuditEvent.RETRY_ATTEMPTED, {
                    "attempt": attempt, "reason": critic_result.rejection_reason,
                }, run_id=run_state.run_id)
            attempt += 1

        dur = (time.perf_counter() - t0) * 1000
        run_state.risk_matrix = critic_result.matrix
        run_state.critic_rejected = critic_result.rejected
        run_state.critic_rejection_reason = critic_result.rejection_reason
        run_state.critic_backend = critic_result.backend
        run_state.circuit_breaker_open = circuit_open

        attempts_note = f" ({attempt} attempt{'s' if attempt > 1 else ''})" if attempt > 1 else ""
        run_state.record_step(DecisionStep(
            step_name="risk_assessment_engine",
            status="FAILED" if critic_result.rejected else "OK",
            detail=f"Backend: {critic_result.backend}, Rejected: {critic_result.rejected}{attempts_note}",
            duration_ms=round(dur, 2),
        ))
        if self._audit:
            if critic_result.rejected:
                self._audit.record(AuditEvent.CRITIC_REJECTED, {
                    "reason": critic_result.rejection_reason, "raw": critic_result.raw,
                }, run_id=run_state.run_id)
            else:
                self._audit.record(AuditEvent.CRITIC_ASSESSED,
                                   critic_result.matrix.model_dump(mode="json"),
                                   run_id=run_state.run_id)

    # -- Stage 5: Verifier ---------------------------------------------------------
    def _verify(self, run_state: RunState) -> None:
        t0 = time.perf_counter()
        if not run_state.critic_rejected and run_state.risk_matrix is not None:
            result = self._verifier.verify(run_state.risk_matrix, run_state.trusted_evidence)
            if not result.valid:
                run_state.critic_rejected = True
                run_state.critic_rejection_reason = f"verifier_check_failed: {result.reason}"
        else:
            result = VerifierResult(
                valid=False, reason="Critic output was rejected prior to verification",
                checks_failed=["pre_verification_critic_rejection"],
            )
        dur = (time.perf_counter() - t0) * 1000
        run_state.verifier_result = result
        run_state.record_step(DecisionStep(
            step_name="verifier_subsystem", status="OK" if result.valid else "FAILED",
            detail=result.reason or "Verification evaluated", duration_ms=round(dur, 2),
        ))

    # -- Stage 6: Deterministic Controller -----------------------------------------
    def _decide(self, run_state: RunState, policy_pack: PolicyPack) -> None:
        from .critic import CriticResult
        from .gate import GateResult

        t0 = time.perf_counter()
        gate_result = GateResult(
            trusted=run_state.trusted_evidence, excluded=run_state.excluded_evidence,
            excluded_ids=run_state.excluded_evidence_ids, missing_required=run_state.missing_required,
            agents_unavailable=run_state.agents_unavailable,
        )
        critic_result = CriticResult(
            matrix=run_state.risk_matrix, rejected=run_state.critic_rejected,
            backend=run_state.critic_backend or "unknown",
            rejection_reason=run_state.critic_rejection_reason,
        )
        outcome = controller.decide(gate_result, critic_result, policy_pack=policy_pack)
        dur = (time.perf_counter() - t0) * 1000

        run_state.confidence = outcome.confidence
        run_state.confidence_breakdown = outcome.confidence_breakdown
        run_state.controller_state = outcome.state
        run_state.decision_reason = outcome.reason
        run_state.request_action = outcome.request_action

        run_state.record_step(DecisionStep(
            step_name="deterministic_controller",
            status=("OK" if outcome.state == ControllerState.AUTO_OPTIMIZE
                    else "WARNING" if outcome.state == ControllerState.INSUFFICIENT_DATA
                    else "FAILED"),
            detail=f"State: {outcome.state.value}, Confidence: {int(outcome.confidence * 100)}%",
            duration_ms=round(dur, 2),
        ))
