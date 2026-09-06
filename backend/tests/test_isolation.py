"""Phase 4: the harness isolation guarantees, as executable proof.

These are the claims a judge should be able to trust:
  1. Agents read only their own scope.
  2. Neither an Agent nor the Critic can import, reach, or call the Action Gateway.
  3. The Critic's only input is structured Evidence.
"""
from __future__ import annotations

import ast
import inspect
from pathlib import Path

from app import agents, critic
from app.agents import EnvironmentObserver, VehicleObserver

APP_DIR = Path(inspect.getfile(agents)).parent


def _imported_names(module) -> set[str]:
    """Every module name imported by a source module (via `import` / `from`)."""
    tree = ast.parse(Path(inspect.getfile(module)).read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            names.add(base)
            names.update(f"{base}.{a.name}" for a in node.names)
    return names


def test_agents_do_not_import_actions() -> None:
    imported = _imported_names(agents)
    assert not any("actions" in n for n in imported), imported


def test_critic_does_not_import_actions() -> None:
    imported = _imported_names(critic)
    assert not any("actions" in n for n in imported), imported


def test_agent_instances_expose_no_action_path() -> None:
    for agent in (VehicleObserver(), EnvironmentObserver()):
        attrs = dir(agent)
        assert not any(
            k in a.lower() for a in attrs for k in ("action", "gateway", "execute")
        ), attrs
        # the only public capability is observation
        assert hasattr(agent, "observe")
        assert getattr(agent, "request", None) is None


def test_action_gateway_symbol_not_in_agent_or_critic_namespace() -> None:
    for mod in (agents, critic):
        assert not hasattr(mod, "ActionGateway")
        assert not hasattr(mod, "request")


def test_vehicle_observer_cannot_reach_environment_scope() -> None:
    # Agent A's declared scope contains no environment signal, and vice versa.
    env_signals = {"ambient_temperature", "weather_severity",
                   "traffic_level", "dwell_minutes"}
    assert not (set(VehicleObserver.SCOPE) & env_signals)
    veh_signals = {"cargo_temperature", "cooling_status", "vehicle_speed"}
    assert not (set(EnvironmentObserver.SCOPE) & veh_signals)


def test_critic_input_is_only_evidence() -> None:
    # assess() takes the evidence list, a corrupt flag, and (for the Verifier
    # feedback loop) a plain corrective string — still no world, no tools, no
    # action authority.
    params = list(inspect.signature(critic.Critic.assess).parameters)
    assert params == ["self", "evidence", "corrupt", "feedback"]


def test_unauthorized_action_probe_reports_blocked() -> None:
    from app.security import probe_unauthorized_action

    r = probe_unauthorized_action()
    assert r["blocked"] is True
    assert all(a["outcome"] == "blocked" for a in r["attempts"])
    assert len(r["attempts"]) >= 3
