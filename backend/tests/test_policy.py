"""Phase 1: policy is a deterministic, boundary-exact contract."""
from __future__ import annotations

from app import policy
from app.schemas import AgentSource, FreshnessStatus


def test_freshness_boundaries() -> None:
    fmax, smax = 120, 300
    assert policy.classify_freshness(0, fmax, smax) == FreshnessStatus.FRESH
    assert policy.classify_freshness(119.9, fmax, smax) == FreshnessStatus.FRESH
    assert policy.classify_freshness(120, fmax, smax) == FreshnessStatus.STALE
    assert policy.classify_freshness(299.9, fmax, smax) == FreshnessStatus.STALE
    assert policy.classify_freshness(300, fmax, smax) == FreshnessStatus.INVALID
    assert policy.classify_freshness(9999, fmax, smax) == FreshnessStatus.INVALID


def test_authorized_source_split() -> None:
    assert policy.authorized_source("cargo_temperature") == AgentSource.AGENT_A
    assert policy.authorized_source("ambient_temperature") == AgentSource.AGENT_B
    assert policy.authorized_source("nonsense") is None


def test_required_signals_span_both_agents() -> None:
    req = policy.required_signals()
    sources = {policy.authorized_source(s) for s in req}
    assert AgentSource.AGENT_A in sources and AgentSource.AGENT_B in sources
