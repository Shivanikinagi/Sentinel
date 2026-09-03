"""Phase 6: the HTTP surface drives every demo scene with no code edits."""
from __future__ import annotations

import os

# Configure BEFORE importing the app so the process-wide harness binds to an
# in-memory DB and the deterministic mock critic.
os.environ["DB_PATH"] = ":memory:"
os.environ["FORCE_MOCK_CRITIC"] = "true"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset():
    client.post("/simulate/reset")
    yield


def test_health_reports_mock_backend() -> None:
    r = client.get("/health").json()
    assert r["ok"] is True and r["critic_backend"] == "mock"


def test_healthy_run_auto_optimizes() -> None:
    client.post("/simulate/scenario", json={"name": "healthy"})
    d = client.post("/runs").json()
    assert d["controller_state"] == "AUTO_OPTIMIZE"
    assert d["confidence"] == 1.0
    # retrievable by run_id
    got = client.get(f"/decisions/{d['run_id']}").json()
    assert got["run_id"] == d["run_id"]


def test_compound_risk_halts_then_human_approves() -> None:
    client.post("/simulate/scenario", json={"name": "compound_risk"})
    d = client.post("/runs").json()
    assert d["controller_state"] == "CRITICAL_HALT"
    action_id = d["escalation_id"]
    pending = client.get("/actions/pending").json()
    assert [p["action_id"] for p in pending] == [action_id]

    approved = client.post(f"/actions/{action_id}/approve",
                           json={"approver": "ops@fleet"}).json()
    assert approved["status"] == "EXECUTED"
    assert client.get("/actions/pending").json() == []


def test_kill_agent_yields_insufficient_data() -> None:
    client.post("/simulate/kill-agent", json={"agent": "agent_b", "disabled": True})
    d = client.post("/runs").json()
    assert d["controller_state"] == "INSUFFICIENT_DATA"


def test_corrupt_llm_is_rejected() -> None:
    client.post("/simulate/corrupt-llm")
    d = client.post("/runs").json()
    assert d["controller_state"] == "INSUFFICIENT_DATA"
    assert d["critic_rejected"] is True
    assert d["risk_matrix"] is None


def test_state_and_audit_endpoints() -> None:
    client.post("/simulate/scenario", json={"name": "compound_risk"})
    client.post("/runs")
    state = client.get("/state").json()
    assert state["scenario"] == "compound_risk"
    assert "switches" in state
    audit = client.get("/audit").json()
    assert any(a["event_type"] == "decision_made" for a in audit)


def test_unknown_scenario_is_400() -> None:
    r = client.post("/simulate/scenario", json={"name": "nope"})
    assert r.status_code == 400


def test_approving_missing_action_is_404() -> None:
    r = client.post("/actions/act_missing/approve", json={"approver": "x"})
    assert r.status_code == 404
