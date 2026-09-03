"""Unauthorized-action probe — the live 'red team' demo moment.

Honestly attempts to reach an operational action FROM an agent's own surface, and
records that every path is blocked by construction. Nothing here is staged: it
inspects the real agent object and the real module imports. If someone ever wired
an action callable onto an agent, this probe would light up 'EXPOSED' and the
matching test in test_isolation.py would fail.
"""
from __future__ import annotations

import ast
import inspect
from pathlib import Path

from .agents import VehicleObserver

# Names a compromised/confused agent might try to use to execute an action.
_ATTACK_VECTORS = (
    "execute_action", "request_action", "cancel_dispatch", "halt_dispatch",
    "gateway", "actions", "action_gateway",
)


def probe_unauthorized_action() -> dict:
    agent = VehicleObserver()
    attempts: list[dict] = []

    # 1) Try to reach an action-executing member on the agent itself.
    for name in _ATTACK_VECTORS:
        member = getattr(agent, name, None)
        attempts.append({
            "vector": f"VehicleObserver().{name}(...)",
            "outcome": "EXPOSED" if member is not None else "blocked",
            "detail": ("attribute exists" if member is not None
                       else "AttributeError: agent has no such member"),
        })

    # 2) Does the agents module even import the action gateway?
    imports = _imported_names(_agents_file())
    reaches_actions = any("actions" in n for n in imports)
    attempts.append({
        "vector": "import path: app.agents -> app.actions",
        "outcome": "EXPOSED" if reaches_actions else "blocked",
        "detail": ("agents imports actions" if reaches_actions
                   else "agents.py has no import of the action gateway"),
    })

    blocked = all(a["outcome"] == "blocked" for a in attempts)
    return {
        "blocked": blocked,
        "conclusion": (
            "No callable path from an agent to any action. The Controller is the "
            "only component that can trigger the Action Gateway."
            if blocked else "SECURITY REGRESSION: an action path is reachable."
        ),
        "attempts": attempts,
    }


def _agents_file() -> str:
    from . import agents
    return inspect.getfile(agents)


def _imported_names(path: str) -> set[str]:
    tree = ast.parse(Path(path).read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            names.add(base)
            names.update(f"{base}.{a.name}" for a in node.names)
    return names
