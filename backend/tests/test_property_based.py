"""Property-based / randomized testing (Hypothesis).

The scenario tests prove the demo works. These prove the harness holds up on
inputs nobody hand-wrote: random signal names, random timestamps (past AND
future), duplicate evidence, arbitrary JSON thrown at the Critic validator, and
fully randomized world states run through the whole pipeline.

Invariants asserted everywhere:
  * Nothing in the harness ever raises on malformed/adversarial input — it
    degrades to INSUFFICIENT_DATA / rejection instead of crashing.
  * confidence is always in [0.0, 1.0] — the confidence.compute() docstring's
    claim to the Critic, not self-reported, must hold even for weird counts.
  * controller_state is always one of exactly 3 valid values.
  * No RiskMatrix reaches the Controller without passing schema validation.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from hypothesis import HealthCheck, given, settings, strategies as st

from app import confidence, gate, policy
from app.controller import decide as controller_decide
from app.critic import Critic
from app.gate import GateResult
from app.pipeline import build_harness
from app.schemas import AgentSource, ControllerState, Evidence
from app.store import Store
from app.world import WorldState

NOW = datetime(2026, 9, 2, 12, 0, 0, tzinfo=timezone.utc)

ALL_SIGNALS = tuple(policy.SIGNAL_SOURCE.keys())
ALL_SOURCES = tuple(AgentSource)

# --------------------------------------------------------------------- gate

evidence_strategy = st.builds(
    Evidence,
    run_id=st.just("r1"),
    vehicle_id=st.just("TRUCK-042"),
    signal=st.one_of(st.sampled_from(ALL_SIGNALS), st.text(min_size=1, max_size=20)),
    value=st.floats(allow_nan=False, allow_infinity=False, width=32),
    unit=st.text(max_size=10),
    source=st.sampled_from(ALL_SOURCES),
    # spans well before "fresh", through "stale", "invalid", AND the future.
    timestamp=st.integers(min_value=-600, max_value=600).map(
        lambda secs: NOW - timedelta(seconds=secs)
    ),
)


@given(st.lists(evidence_strategy, max_size=15))
@settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
def test_gate_never_crashes_and_partitions_all_evidence(evs: list[Evidence]) -> None:
    result = gate.evaluate(evs, now=NOW)
    # every input evidence id lands in exactly one of trusted/excluded
    got_ids = {e.evidence_id for e in result.trusted} | {e.evidence_id for e in result.excluded}
    assert got_ids == {e.evidence_id for e in evs}
    assert len(result.trusted) + len(result.excluded) == len(evs)
    # trusted evidence is always from its policy-authorized source
    for e in result.trusted:
        assert e.source == policy.authorized_source(e.signal)


@given(st.lists(evidence_strategy, max_size=10),
      st.lists(st.sampled_from(ALL_SOURCES), max_size=2))
@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
def test_gate_handles_future_timestamps_without_crashing(
    evs: list[Evidence], unavailable: list[AgentSource]
) -> None:
    # future timestamps -> negative age; must clamp, never go negative or crash.
    result = gate.evaluate(evs, unavailable, now=NOW)
    for e in result.trusted + result.excluded:
        assert e.age_seconds >= 0.0


@given(st.sampled_from(ALL_SIGNALS), st.integers(min_value=1, max_value=6))
@settings(max_examples=50)
def test_duplicate_evidence_for_same_signal_stays_bounded(
    signal: str, n: int
) -> None:
    """A chatty/misbehaving agent emitting the SAME signal n times must not let
    `trusted` exceed the expected signal count confidence relies on as a fixed
    denominator (regression guard for the confidence >1.0 class of bug)."""
    source = policy.authorized_source(signal)
    evs = [
        Evidence(run_id="r1", vehicle_id="T", signal=signal, value=float(i),
                 unit="x", source=source, timestamp=NOW)
        for i in range(n)
    ]
    result = gate.evaluate(evs, now=NOW)
    conf = confidence.compute(len(result.trusted), policy.expected_signal_count(),
                              contradiction=False)
    assert 0.0 <= conf <= 1.0, (
        f"confidence {conf} escaped [0,1] with {len(result.trusted)} trusted "
        f"duplicates of '{signal}' against expected={policy.expected_signal_count()}"
    )


# ---------------------------------------------------------------- confidence

@given(st.integers(min_value=0, max_value=1000),
      st.integers(min_value=0, max_value=1000),
      st.booleans())
@settings(max_examples=300)
def test_confidence_always_in_unit_interval(
    trusted: int, expected: int, contradiction: bool
) -> None:
    conf = confidence.compute(trusted, expected, contradiction)
    assert 0.0 <= conf <= 1.0, (trusted, expected, contradiction, conf)


@given(st.integers(min_value=1, max_value=1000))
@settings(max_examples=50)
def test_confidence_zero_trusted_is_zero(expected: int) -> None:
    assert confidence.compute(0, expected, contradiction=False) == 0.0
    assert confidence.compute(0, expected, contradiction=True) == 0.0


# ------------------------------------------------------------- critic fuzzing

# Arbitrary JSON-shaped values thrown directly at the validator — the "what if
# a model returns garbage" case. Every one of these must be rejected, not raise.
json_scalars = st.one_of(st.none(), st.booleans(), st.integers(), st.floats(allow_nan=False),
                         st.text(max_size=30))
json_value = st.recursive(
    json_scalars,
    lambda children: st.one_of(
        st.lists(children, max_size=4),
        st.dictionaries(st.text(max_size=10), children, max_size=4),
    ),
    max_leaves=15,
)


class _FuzzBackend:
    name = "fuzz"
    def __init__(self, payload):
        self._payload = payload
    def produce(self, evidence):
        return self._payload


@given(json_value)
@settings(max_examples=300, suppress_health_check=[HealthCheck.too_slow])
def test_critic_validation_never_crashes_on_arbitrary_json(payload) -> None:
    result = Critic(_FuzzBackend(payload)).assess([])
    assert result.rejected in (True, False)
    if not result.rejected:
        # the only way this is accepted is if it happened to be a fully valid
        # RiskMatrix-shaped dict -- still must be a real RiskMatrix instance.
        assert result.matrix is not None


@given(st.dictionaries(st.text(min_size=1, max_size=15), json_value, max_size=8))
@settings(max_examples=200)
def test_critic_validation_rejects_or_produces_valid_matrix(payload: dict) -> None:
    result = Critic(_FuzzBackend(payload)).assess([])
    if not result.rejected:
        assert result.matrix.risk_level.value in ("LOW", "MEDIUM", "HIGH")
        assert isinstance(result.matrix.contradiction_detected, bool)


# ---------------------------------------------------------------- controller

gate_result_strategy = st.builds(
    GateResult,
    trusted=st.lists(evidence_strategy, max_size=9),
    agents_unavailable=st.lists(st.sampled_from(ALL_SOURCES), max_size=2),
    missing_required=st.lists(st.sampled_from(policy.required_signals()), max_size=3),
)


@given(gate_result_strategy, st.booleans(), st.sampled_from(["LOW", "MEDIUM", "HIGH", None]),
      st.booleans())
@settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
def test_controller_always_returns_a_valid_state(
    gr: GateResult, critic_rejected: bool, risk_level, contradiction: bool
) -> None:
    from app.critic import CriticResult
    from app.schemas import RiskLevel, RiskMatrix

    matrix = None
    if not critic_rejected and risk_level is not None:
        matrix = RiskMatrix(risk_level=RiskLevel(risk_level),
                            contradiction_detected=contradiction,
                            reasoning_summary="fuzz")
    cr = CriticResult(matrix=matrix, rejected=critic_rejected, backend="fuzz")
    outcome = controller_decide(gr, cr)
    assert outcome.state in (ControllerState.AUTO_OPTIMIZE,
                             ControllerState.INSUFFICIENT_DATA,
                             ControllerState.CRITICAL_HALT)
    assert 0.0 <= outcome.confidence <= 1.0
    # request_action is ONLY ever true alongside CRITICAL_HALT
    if outcome.request_action:
        assert outcome.state == ControllerState.CRITICAL_HALT


# ------------------------------------------------------------------ pipeline

float_field = st.floats(min_value=-50, max_value=200, allow_nan=False, allow_infinity=False)


@given(
    cargo=float_field, tyre_p=float_field, tyre_t=float_field,
    cooling=st.sampled_from([0.0, 1.0, 0.5, -1.0, 2.0]),  # incl. out-of-domain
    speed=float_field, ambient=float_field, weather=float_field,
    traffic=float_field, dwell=float_field,
    kill_a=st.booleans(), kill_b=st.booleans(), corrupt=st.booleans(),
    stale_signal=st.one_of(st.none(), st.sampled_from(ALL_SIGNALS)),
)
@settings(max_examples=60, suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture])
def test_full_pipeline_never_crashes_on_random_world(
    cargo, tyre_p, tyre_t, cooling, speed, ambient, weather, traffic, dwell,
    kill_a, kill_b, corrupt, stale_signal,
) -> None:
    from app.config import Settings

    store = Store(":memory:")
    try:
        h = build_harness(store, Settings(force_mock_critic=True,
                                          auto_approve_auto_tier=True))
        w = WorldState()
        w.vehicle.cargo_temperature = cargo
        w.vehicle.tyre_pressure = tyre_p
        w.vehicle.tyre_temperature = tyre_t
        w.vehicle.cooling_status = cooling
        w.vehicle.vehicle_speed = speed
        w.environment.ambient_temperature = ambient
        w.environment.weather_severity = weather
        w.environment.traffic_level = traffic
        w.environment.dwell_minutes = dwell
        w.agent_a_disabled = kill_a
        w.agent_b_disabled = kill_b
        w.corrupt_critic = corrupt
        w.force_stale_signal = stale_signal

        decision = h.run(w)

        assert decision.controller_state in (
            ControllerState.AUTO_OPTIMIZE, ControllerState.INSUFFICIENT_DATA,
            ControllerState.CRITICAL_HALT,
        )
        assert 0.0 <= decision.confidence <= 1.0
        if kill_a or kill_b or corrupt:
            # the harness must never auto-optimize on incomplete/rejected input
            assert decision.controller_state != ControllerState.AUTO_OPTIMIZE
        if decision.escalation_id:
            assert decision.controller_state == ControllerState.CRITICAL_HALT
        if decision.critic_rejected:
            assert decision.risk_matrix is None
    finally:
        store.close()
