"""Scripted rehearsal driver for the Fleet-Harness demo.

Drives the six demo scenes against a running backend (default http://localhost:8000)
so you can rehearse the flow with consistent, readable output. Pure stdlib.

Usage:
    python scripts/demo.py                 # pause between scenes (presenter-paced)
    python scripts/demo.py --auto          # run straight through
    python scripts/demo.py --base URL      # point at another host
"""
from __future__ import annotations

import argparse
import json
import urllib.request

BASE = "http://localhost:8000"


def call(method: str, path: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        f"{BASE}{path}", data=data, method=method,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())


def line(char: str = "-") -> None:
    print(char * 68)


def show(decision: dict) -> None:
    print(f"  STATE       : {decision['controller_state']}")
    print(f"  reason      : {decision['reason']}")
    print(f"  confidence  : {decision['confidence'] * 100:.0f}%")
    if decision.get("risk_matrix"):
        rm = decision["risk_matrix"]
        print(f"  risk        : {rm['risk_level']}  contradiction={rm['contradiction_detected']}")
        if rm["risk_factors"]:
            print(f"  factors     : {', '.join(rm['risk_factors'])}")
    if decision.get("critic_rejected"):
        print("  critic      : REJECTED by schema validation")
    if decision.get("escalation_id"):
        print(f"  escalation  : action {decision['escalation_id']} (pending approval)")


def scene(title: str, pause: bool) -> None:
    line("=")
    print(title)
    line("=")
    if pause:
        input("  (enter to run) ")


def main() -> None:
    global BASE
    ap = argparse.ArgumentParser()
    ap.add_argument("--auto", action="store_true", help="no pauses")
    ap.add_argument("--base", default=BASE)
    args = ap.parse_args()
    BASE = args.base
    pause = not args.auto

    call("POST", "/simulate/reset")
    h = call("GET", "/health")
    print(f"backend up | critic={h['critic_backend']} | model={h['model']}\n")

    scene("SCENE 1 — Healthy run  ->  AUTO_OPTIMIZE", pause)
    call("POST", "/simulate/scenario", {"name": "healthy"})
    show(call("POST", "/runs"))

    scene("SCENE 2 — Compound risk  ->  CRITICAL_HALT (contradiction)", pause)
    call("POST", "/simulate/scenario", {"name": "compound_risk"})
    d = call("POST", "/runs")
    show(d)

    scene("SCENE 3 — Human approves the halt (Layer 2)", pause)
    action_id = d["escalation_id"]
    approved = call("POST", f"/actions/{action_id}/approve", {"approver": "ops@fleet"})
    print(f"  action {action_id} -> {approved['status']}, "
          f"escalation record {approved['escalation_id']} created")

    scene("SCENE 4 — Kill Agent B  ->  INSUFFICIENT_DATA (stays up)", pause)
    call("POST", "/simulate/scenario", {"name": "healthy"})
    call("POST", "/simulate/kill-agent", {"agent": "agent_b", "disabled": True})
    show(call("POST", "/runs"))
    call("POST", "/simulate/kill-agent", {"agent": "agent_b", "disabled": False})

    scene("SCENE 5 — Corrupt Critic output  ->  schema rejection", pause)
    call("POST", "/simulate/corrupt-llm")
    show(call("POST", "/runs"))

    scene("SCENE 6 — Stale evidence excluded (stretch)", pause)
    call("POST", "/simulate/stale-signal", {"signal": "cargo_temperature"})
    show(call("POST", "/runs"))
    call("POST", "/simulate/stale-signal", {"signal": None})

    scene("SCENE 7 — Unauthorized action attempt  ->  blocked", pause)
    probe = call("POST", "/simulate/unauthorized-action")
    print(f"  blocked     : {probe['blocked']}")
    for a in probe["attempts"]:
        print(f"    [{a['outcome']:>7}] {a['vector']}")
    print(f"  conclusion  : {probe['conclusion']}")

    line("=")
    print("Done. 'When the AI fails, the operation does not.'")


if __name__ == "__main__":
    main()
