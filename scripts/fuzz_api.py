"""Randomized stress test against a LIVE backend (stdlib only, no deps).

Unlike the Hypothesis property tests (unit-level, in-process), this drives the
real HTTP surface with random combinations of scenario + switches + concurrent
approve/reject calls, to catch anything that only shows up through the API and
the real SQLite store (races on the pending-actions list, double-approve via
two clients, malformed request bodies, etc).

    python scripts/fuzz_api.py --requests 300
    python scripts/fuzz_api.py --requests 300 --base http://localhost:8000

Last verified: 2026-09-06.
"""
from __future__ import annotations

import argparse
import json
import random
import threading
import urllib.error
import urllib.request

BASE = "http://localhost:8000"
SCENARIOS = ["healthy", "compound_risk", "nonexistent_scenario_xyz"]  # incl. invalid
SIGNALS = [
    "cargo_temperature", "tyre_pressure", "tyre_temperature", "cooling_status",
    "vehicle_speed", "ambient_temperature", "weather_severity", "traffic_level",
    "dwell_minutes", "", "not_a_real_signal", None,
]
VALID_STATES = {"AUTO_OPTIMIZE", "INSUFFICIENT_DATA", "CRITICAL_HALT"}


class Fail(Exception):
    pass


def call(method: str, path: str, body=None, expect_ok: bool = True):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        f"{BASE}{path}", data=data, method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


def check(cond: bool, msg: str) -> None:
    if not cond:
        raise Fail(msg)


def random_action() -> None:
    """One randomized step: mutate state, run, or hit the action gateway."""
    choice = random.random()

    if choice < 0.15:
        status, _ = call("POST", "/simulate/scenario", {"name": random.choice(SCENARIOS)})
        check(status in (200, 400), f"scenario returned unexpected status {status}")

    elif choice < 0.30:
        agent = random.choice(["agent_a", "agent_b", "agent_c_invalid"])
        status, _ = call("POST", "/simulate/kill-agent",
                         {"agent": agent, "disabled": random.choice([True, False])})
        check(status in (200, 422), f"kill-agent returned unexpected status {status}")

    elif choice < 0.40:
        status, _ = call("POST", "/simulate/corrupt-llm")
        check(status == 200, f"corrupt-llm returned {status}")

    elif choice < 0.50:
        status, _ = call("POST", "/simulate/stale-signal",
                         {"signal": random.choice(SIGNALS)})
        check(status in (200, 422), f"stale-signal returned {status}")

    elif choice < 0.90:
        status, decision = call("POST", "/runs")
        check(status == 200, f"/runs returned {status}: {decision}")
        check(decision["controller_state"] in VALID_STATES,
             f"invalid controller_state: {decision.get('controller_state')}")
        check(0.0 <= decision["confidence"] <= 1.0,
             f"confidence out of range: {decision['confidence']}")
        if decision.get("critic_rejected"):
            check(decision["risk_matrix"] is None,
                 "risk_matrix present despite critic_rejected=True")
        if decision.get("escalation_id"):
            check(decision["controller_state"] == "CRITICAL_HALT",
                 "escalation_id set without CRITICAL_HALT")
            # try to approve/reject a random pending action — including ones
            # that may already be resolved by a concurrent fuzz thread.
            action_id = decision["escalation_id"]
            verb = random.choice(["approve", "reject"])
            payload = {"approver": "fuzzer"} if verb == "approve" else \
                {"approver": "fuzzer", "reason": "fuzz"}
            status, _ = call("POST", f"/actions/{action_id}/{verb}", payload,
                             expect_ok=False)
            check(status in (200, 404, 409),
                 f"{verb} on {action_id} returned unexpected {status}")

    else:
        status, _ = call("GET", "/actions/pending")
        check(status == 200, f"/actions/pending returned {status}")
        status, _ = call("GET", "/audit?limit=5")
        check(status == 200, f"/audit returned {status}")
        status, _ = call("GET", "/state")
        check(status == 200, f"/state returned {status}")


def worker(n: int, errors: list, lock: threading.Lock) -> None:
    for _ in range(n):
        try:
            random_action()
        except Exception as e:  # noqa: BLE001 - fuzz harness, capture everything
            with lock:
                errors.append(repr(e))


def main() -> int:
    global BASE
    ap = argparse.ArgumentParser()
    ap.add_argument("--requests", type=int, default=200)
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--base", default=BASE)
    ap.add_argument("--seed", type=int, default=None)
    args = ap.parse_args()
    BASE = args.base
    if args.seed is not None:
        random.seed(args.seed)

    status, _ = call("POST", "/simulate/reset")
    print(f"reset -> {status}. Fuzzing {args.requests} requests across "
          f"{args.threads} threads against {BASE} ...")

    errors: list[str] = []
    lock = threading.Lock()
    per_thread = args.requests // args.threads
    threads = [threading.Thread(target=worker, args=(per_thread, errors, lock))
              for _ in range(args.threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    if errors:
        print(f"\nFAILED — {len(errors)} invariant violation(s):")
        for e in errors[:20]:
            print(f"  - {e}")
        return 1

    print(f"\nOK — {args.requests} randomized requests, 0 invariant violations, "
          f"server stayed up throughout.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
