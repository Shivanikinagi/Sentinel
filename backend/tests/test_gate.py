"""Phase 1: the trust gate excludes what it must and flags what's missing."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app import gate
from app.schemas import AgentSource, Evidence, FreshnessStatus

NOW = datetime(2026, 9, 2, 12, 0, 0, tzinfo=timezone.utc)


def _ev(signal: str, source: AgentSource, age_s: float = 0.0,
        value: float = 1.0) -> Evidence:
    return Evidence(
        run_id="r1", vehicle_id="TRUCK-042", signal=signal, value=value,
        unit="x", source=source, timestamp=NOW - timedelta(seconds=age_s),
    )


def _healthy_set() -> list[Evidence]:
    return [
        _ev("cargo_temperature", AgentSource.AGENT_A, value=4.0),
        _ev("cooling_status", AgentSource.AGENT_A, value=1.0),
        _ev("ambient_temperature", AgentSource.AGENT_B, value=22.0),
    ]


def test_all_fresh_authorized_are_trusted() -> None:
    res = gate.evaluate(_healthy_set(), now=NOW)
    assert len(res.trusted) == 3
    assert res.excluded == [] and res.missing_required == []
    assert set(res.agents_reporting) == {AgentSource.AGENT_A, AgentSource.AGENT_B}
    assert all(e.status == FreshnessStatus.FRESH for e in res.trusted)


def test_stale_required_signal_is_excluded_and_flagged_missing() -> None:
    ev = _healthy_set()
    ev[0] = _ev("cargo_temperature", AgentSource.AGENT_A, age_s=200, value=9.0)  # stale
    res = gate.evaluate(ev, now=NOW)
    assert "cargo_temperature" not in {e.signal for e in res.trusted}
    assert "ev" not in res.excluded_ids  # sanity: real ids
    assert ev[0].evidence_id in res.excluded_ids
    assert "cargo_temperature" in res.missing_required
    assert any("stale" in n for n in res.gate_notes)


def test_invalid_evidence_excluded() -> None:
    ev = _healthy_set()
    ev[2] = _ev("ambient_temperature", AgentSource.AGENT_B, age_s=400)  # invalid
    res = gate.evaluate(ev, now=NOW)
    assert "ambient_temperature" in res.missing_required
    assert any("invalid" in n for n in res.gate_notes)


def test_wrong_source_is_excluded_for_provenance() -> None:
    # cargo_temperature emitted by Agent B — must be rejected on provenance.
    spoof = _ev("cargo_temperature", AgentSource.AGENT_B, value=4.0)
    res = gate.evaluate([spoof, *_healthy_set()[1:]], now=NOW)
    assert spoof.evidence_id in res.excluded_ids
    assert any("wrong source" in n for n in res.gate_notes)
    assert "cargo_temperature" in res.missing_required


def test_unavailable_agent_forces_missing_required() -> None:
    # Only Agent A reports; Agent B is down -> ambient_temperature missing.
    only_a = [e for e in _healthy_set() if e.source == AgentSource.AGENT_A]
    res = gate.evaluate(only_a, unavailable=[AgentSource.AGENT_B], now=NOW)
    assert "ambient_temperature" in res.missing_required
    assert AgentSource.AGENT_B in res.agents_unavailable
    assert any("agent unavailable: agent_b" in n for n in res.gate_notes)


def test_duplicate_signal_readings_are_deduped_to_the_freshest() -> None:
    # A chatty/misbehaving agent emits cargo_temperature twice; only the
    # freshest reading may be trusted, the older one is excluded as superseded.
    older = _ev("cargo_temperature", AgentSource.AGENT_A, age_s=60, value=5.0)
    newer = _ev("cargo_temperature", AgentSource.AGENT_A, age_s=1, value=6.0)
    res = gate.evaluate([older, newer, *_healthy_set()[1:]], now=NOW)
    trusted_cargo = [e for e in res.trusted if e.signal == "cargo_temperature"]
    assert len(trusted_cargo) == 1 and trusted_cargo[0].evidence_id == newer.evidence_id
    assert older.evidence_id in res.excluded_ids
    assert any("superseded" in n for n in res.gate_notes)


def test_unknown_signal_excluded() -> None:
    weird = _ev("gremlin_level", AgentSource.AGENT_A)
    res = gate.evaluate([*_healthy_set(), weird], now=NOW)
    assert weird.evidence_id in res.excluded_ids
    assert any("unknown signal" in n for n in res.gate_notes)
    # the healthy required set is still intact
    assert res.missing_required == []
