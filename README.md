# Fleet-Harness

An AI **decision-control layer** for fleet operations. It sits above telematics data
and governs what AI agents can access, whether evidence can be trusted, whether the
AI's conclusion is supported, and what actions may actually execute versus merely be
recommended.

> **The principle:** AI provides intelligence. The harness provides trust
> boundaries. Deterministic code provides authority. **The LLM is never the final
> authority over an operational action.**

Scenario: a refrigerated cold-chain delivery truck (`TRUCK-042`).

---

## What makes this more than a demo

Five responsibilities are kept in **separate modules** and never collapsed into one
LLM call — and each guarantee is backed by a **test**, not a claim:

| Layer | Module | Guarantee |
|---|---|---|
| **Intelligence** | `agents.py`, `critic.py` | Agents isolated by code; the Risk Assessment Engine sees only structured evidence |
| **Evidence** | `gate.py` | Freshness + provenance + completeness; stale/invalid excluded |
| **Policy** | `policy_packs.py` | Pluggable domain policy packs (Cold Chain, Tyre Safety); deterministic thresholds, no hardcoded single domain |
| **Decision** | `controller.py`, `confidence.py` | 3-state machine; confidence computed in code, never by the LLM |
| **Authority** | `actions.py` | Action Gateway with human-in-the-loop approval (Layer 2) |

- No LLM output reaches the Controller without passing strict `RiskMatrix`
  validation (`extra="forbid"`). Malformed output is **rejected**, not coerced.
- No agent or Risk Assessment Engine has a code path to execute a fleet action —
  proven in `tests/test_isolation.py`.
- A killed agent or a corrupt model degrades to `INSUFFICIENT_DATA`; the harness
  stays up.
- SQLite append-only audit log survives a mid-demo restart and makes replay cheap.

### The Harness Runtime

Everything above plugs into one runtime, not a bare function call
(`backend/app/supervisor.py`, `run_state.py`, `planner.py`, `retry_engine.py`,
`policy_packs.py`, `memory.py`):

```
Planner → Supervisor(agents → Trust Gate [4 sub-stages] → Correlation →
  Risk Assessment Engine [retry + circuit breaker] → Verifier →
  Deterministic Controller)
→ Harness (persists evidence + decision, requests an action on CRITICAL_HALT)
→ Store / Action Gateway / Audit
```

- **Supervisor** starts each agent, times every stage, retries a failed Risk
  Assessment Engine call, and assembles the execution trace.
- **RunState** (`run_state.py`) is the single object every stage reads and
  writes — evidence, confidence, completed/failed agents, decision, trace —
  instead of a chain of ad hoc local variables.
- **Planner** decides which agents run and whether in parallel.
- **RetryEngine** bounds retry around the one call that crosses a real network
  boundary (the Risk Assessment Engine backend); distinct from the
  CircuitBreaker, which decides whether to attempt the call at all.
- **PolicyEngine** (`policy_packs.py`) selects the active domain pack — the
  Trust Gate, Correlation Engine, and Risk Assessment Engine all read from it.
  Switching packs live (`POST /policy/active`) changes what's required and how
  risk is reasoned about, with zero code changes to gate/critic/controller.
- **Memory** (`memory.py`) tracks a signal across a vehicle's past runs
  (`GET /vehicles/{id}/trend`) instead of judging one snapshot.
- **Metrics** (`metrics.py`) aggregates run outcomes, retries, evidence
  rejected, and action counts over everything persisted (`GET /metrics`).
- **Event Bus** (`events.py`) — every stage publishes a typed event
  (`RUN_STARTED`, `PLANNING_FINISHED`, `AGENT_UNAVAILABLE`, `GATE_EVALUATED`,
  `RETRY_ATTEMPTED`, `CRITIC_ASSESSED`/`REJECTED`, `DECISION_MADE`,
  `RUN_COMPLETED`, …) instead of calling Audit directly. Audit is one
  subscriber (`audit_sink`), not the mechanism itself — the same vocabulary
  still lands in the audit table unchanged. `GET /events/types` lists the
  vocabulary; `GET /events/recent` reads the bus's own ring buffer.
- **Incident Memory** (`incidents.py`) — distinct from Memory's routine signal
  trend: a queryable history of past `CRITICAL_HALT` runs joined with how the
  resulting action was resolved (`GET /incidents`).
- **Composite Confidence** (`confidence.compute_composite`) — a second,
  richer confidence view alongside the tested evidence-completeness formula:
  `evidence quality × verifier score × gate cleanliness × policy compliance ×
  historical reliability`, each factor independently observable, not
  self-reported by the LLM.

`pipeline.Harness` / `build_harness()` remain the public entry point — internally
they now delegate to the Supervisor, so the whole runtime is a drop-in, not a
rewrite of the tested pipeline.

---

## Quickstart

### 1. Backend (FastAPI)

```bash
cd backend
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # Windows
# source .venv/bin/activate && pip install -r requirements.txt   # macOS/Linux
.venv/Scripts/python -m uvicorn app.main:app --port 8000
```

The backend runs **without any API key** — a deterministic `MockCritic` runs
automatically, so the demo never depends on the network. To use a real model,
copy `.env.example` to `.env` and set `OPENROUTER_API_KEY` (any OpenRouter model
id in `LLM_MODEL`). Validate the real path first:

```bash
cd backend && .venv/Scripts/python ../scripts/check_openrouter.py
```

It sends the compound-risk evidence to your model and prints the **validated**
`RiskMatrix` (or the exact error), confirming the key + model before the demo.

### 2. Frontend (React + Vite)

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173
```

The dashboard polls the backend live. Use the buttons across the top to drive
every scene; the Controller banner, evidence panels, Critic card, pending actions,
and audit log all update automatically.

**Simple / Technical toggle** (top right): the dashboard defaults to **Simple**
— plain-English labels a non-technical operator can read at a glance ("Everything
looks good", "Cargo Temperature: 4 celsius", "Cooling System: Running"), with the
internal harness vocabulary (agent names, RiskMatrix, gate notes, raw audit JSON)
hidden. Switch to **Technical** to reveal that vocabulary as small captions
alongside the plain-English text — for judges evaluating the harness design, not
replacing the friendly copy. See `frontend/src/humanize.ts` for the translation layer.

### 3. Scripted rehearsal (optional)

With the backend running:

```bash
python scripts/demo.py            # presenter-paced (enter between scenes)
python scripts/demo.py --auto     # straight through
```

---

## Demo scenes

1. **Healthy** → `AUTO_OPTIMIZE` (100% confidence).
2. **Compound risk** (cooling ON while cargo climbs, hot ambient, long dwell) →
   Critic flags a **contradiction** → `CRITICAL_HALT`, and a HUMAN-tier action
   opens for approval.
3. **Approve** the halt → executed, an immutable escalation record is created; the
   full chain is in the audit log.
4. **Kill Agent B** → `INSUFFICIENT_DATA` at 56% confidence; the system stays up.
5. **Corrupt LLM** → schema rejection → `INSUFFICIENT_DATA` (one-shot).
6. **Stale cargo temp** (stretch) → evidence excluded → `INSUFFICIENT_DATA`.
7. **Unauthorized action attempt** (red team) → every path from an agent to an
   action is blocked; the dashboard's *Authorization Boundary* panel proves it live.
8. **Simulated network blip** (Simulation Lab) → the Risk Assessment Engine fails
   once, the RetryEngine retries and recovers within the same run — a live
   `Retry #1 → Risk Assessment Engine (2 attempts)` row on the Harness Runtime
   page's timeline.
9. **Switch policy pack** (Harness Runtime page) → select "Tyre Safety Policy" and
   run again: the Trust Gate now requires tyre signals instead of cargo signals,
   and the Risk Assessment Engine reasons about tyre pressure/temperature instead
   of cold-chain thresholds — zero code changes, same gate/critic/controller.

---

## Tests

```bash
cd backend
.venv/Scripts/python -m pytest
```

Fast, deterministic, and **network-free** (mock critic). Covers the gate, policy,
critic validation, confidence, controller table, action gateway, isolation
guarantees, every pipeline scenario, the HTTP surface, and the Harness Runtime
additions (Supervisor/RunState wiring, retry recovery, gate-stage breakdown,
policy-pack switching, confidence breakdown, event bus, incident memory,
composite confidence, metrics, memory) — 98 tests.

### Property-based / fuzz testing

`tests/test_property_based.py` uses [Hypothesis](https://hypothesis.readthedocs.io)
to generate hundreds of random inputs per property rather than hand-written
cases: random signal names, timestamps from the past *and* future, duplicate
evidence, arbitrary JSON thrown straight at the Critic validator, and fully
randomized world states run through the whole pipeline. It asserts invariants
like "confidence is always in [0, 1]" and "the controller only ever returns one
of its 3 valid states" hold for every input, not just the ones in the demo script.

This actually caught two real bugs during development:

1. `confidence.compute()` could return values above 1.0 if an agent emitted a
   duplicate reading for the same signal (nothing capped `trusted_count` at the
   expected denominator). Fixed by deduplicating evidence per-signal in the
   gate (keeping the freshest reading) plus a defensive clamp in `confidence.py`.
2. **A genuine concurrency bug in `store.py`**, found by the live-HTTP fuzzer
   below: read methods (`recent_audit`, `get_decision`, ...) didn't take the
   same lock the write methods did. Under concurrent requests this reliably
   (every run, dozens of times per run) produced `TypeError`, `IndexError`,
   and `InterfaceError` crashes from unsynchronized access to the shared
   `sqlite3.Connection`. Fixed by serializing every method that touches the
   connection — reads included — through the one lock (`tests/test_store.py::
   test_concurrent_reads_and_writes_never_crash_or_corrupt` is the regression
   test; it fails reliably against the old code and passes cleanly against the fix).

```bash
cd backend && .venv/Scripts/python -m pytest tests/test_property_based.py -v
```

There's also a live-HTTP concurrency fuzzer (stdlib only, no deps) that hits a
**running** backend with random scenario/switch combinations and concurrent
approve/reject races from multiple threads — this exercises the real SQLite
store and HTTP layer, which the in-process Hypothesis tests don't touch:

```bash
python scripts/fuzz_api.py --requests 400 --threads 6
```

---

## Project layout

```
backend/app/
  agents.py     world.py      config.py       schemas.py
  gate.py       policy.py     policy_packs.py critic.py      confidence.py
  correlation.py verifier.py  circuit_breaker.py tools.py    security.py
  controller.py  actions.py   store.py        audit.py       events.py
  planner.py     retry_engine.py  run_state.py supervisor.py pipeline.py  main.py
  memory.py      metrics.py   incidents.py
backend/tests/  ...
frontend/src/   App.tsx  components.tsx  api.ts  types.ts  styles.css
  pages/HarnessRuntime.tsx
  components/HarnessRuntimeDiagram.tsx  SupervisorConsole.tsx  HarnessMetricsPanel.tsx
             PolicyPackCard.tsx  ConfidenceBreakdownCard.tsx  VehicleTrendCard.tsx
             IncidentMemoryPanel.tsx  IsolationDemoCard.tsx  WorldStateCard.tsx
             DecisionCertificate.tsx
scripts/demo.py
```

## API surface

`POST /runs[?policy_pack=]` · `GET /decisions/{run_id}` · `GET /decisions` ·
`GET /state` · `GET /audit` · `GET /actions/pending` · `GET /actions/{id}` ·
`POST /actions/{id}/approve|reject` ·
`POST /simulate/{scenario,kill-agent,corrupt-llm,stale-signal,transient-error,reset}` ·
`GET /metrics` · `GET|POST /policy/packs|active` ·
`GET /vehicles/{vehicle_id}/trend?signal=` · `GET /incidents?vehicle_id=` ·
`GET /events/types` · `GET /events/recent`

Interactive docs at `http://localhost:8000/docs`.
