# Fleet-Harness — Implementation Plan

**Target:** A genuinely good, production-shaped build of the AI decision-control harness — not just a hackathon MVP.
**Scope decision:** All `[BUILD]` layers to a high standard **+ Layer 2** (real Action Gateway with human-in-the-loop approval and full audit trail). Remaining `[FUTURE]` layers (multi-tenancy, IAM, OPA, Kafka, K8s) are left as *clean seams*, not implemented.
**Stack:** Python 3.11+ / FastAPI / Pydantic v2 · SQLite (durable, replay-ready) · React + Vite + TypeScript · LLM provider-agnostic (OpenRouter default) + deterministic offline mock.

> **Design north star (never violated):** AI provides intelligence. The harness provides trust boundaries. Deterministic code provides authority. The LLM is *never* the final authority over an operational action. The five responsibilities — **Intelligence, Evidence, Policy, Decision, Authority** — stay in separate modules and are never collapsed into one LLM call.

---

## 1. Current state

| File | Status | Notes |
|---|---|---|
| `backend/app/schemas.py` | ✅ Keep as-is | Strong contract layer. `RiskMatrix` is `extra="forbid"`. `DecisionTrace`/`ControllerDecision` already anticipate the gate, confidence, escalation. |
| `backend/app/world.py` | ✅ Keep, extend scenarios | Single source of raw truth + all demo switches. |
| `backend/app/agents.py` | ✅ Keep, minor tidy | Code-enforced isolation is real. Normalize the two `observe()` signatures (see §7 tidy). |
| Everything downstream | ❌ To build | ~70% of the system. |

---

## 2. Target module map

```
backend/app/
  config.py       [NEW] pydantic-settings: OpenRouter key/model/base_url, freshness thresholds, approval mode
  schemas.py      [keep] contracts (+ small additions: ActionRequest, ApprovalTier, RunSummary)
  world.py        [keep] raw truth + demo switches (+ 1-2 more scenarios)
  agents.py       [keep] Agent A / Agent B — Intelligence (observers)
  policy.py       [NEW] Policy — deterministic cold-chain thresholds + required-signal rules (OPA seam)
  gate.py         [NEW] Evidence — trust gate: freshness, provenance, exclusion, completeness
  critic.py       [NEW] Intelligence — LLM Consensus Critic (OpenRouter + mock) → validated RiskMatrix
  confidence.py   [NEW] Decision — confidence computed in CODE, never self-reported
  controller.py   [NEW] Decision — deterministic 3-state machine
  actions.py      [NEW] Authority — Action Gateway (Layer 2): request → approval tier → execute
  pipeline.py     [NEW] Orchestrator — ties layers, persists, audits, returns ControllerDecision
  store.py        [NEW] SQLite repository (append-only audit; replay-ready)
  audit.py        [NEW] append-only audit writer (thin over store)
  main.py         [NEW] FastAPI app + routers + live push (WebSocket/SSE)
backend/tests/
  test_gate.py  test_policy.py  test_critic_validation.py  test_confidence.py
  test_controller.py  test_isolation.py  test_actions.py
  test_pipeline_scenarios.py  test_api.py
backend/requirements.txt  ·  backend/.env.example  ·  backend/pyproject.toml (optional)
frontend/                 [NEW] Vite + React + TS dashboard
README.md  ·  IMPLEMENTATION_PLAN.md (this file)  ·  scripts/demo.py (rehearsal driver)
```

---

## 3. The five layers — responsibilities & contracts

### 3.1 Intelligence — Agents (exists) + Critic (new)
- **Agents A/B:** already isolated by code. Emit `list[Evidence]`. No reference to each other, the Critic, or actions.
- **Critic:** receives **only** `list[Evidence]` (structured, already gated). Never sees raw world state or tools. Returns a **schema-validated** `RiskMatrix` or is rejected. Provider-agnostic via a `CriticBackend` protocol:
  - `OpenRouterCritic` — real call via `httpx` to `https://openrouter.ai/api/v1/chat/completions`.
  - `MockCritic` — deterministic, derives a plausible `RiskMatrix` from `policy.py` thresholds. **Runs whenever no API key is set**, so the demo never depends on live network.
  - `corrupt_critic` switch forces malformed output (bad JSON / missing field / extra field) from *either* backend → exercises schema rejection.

### 3.2 Evidence — Trust Gate (`gate.py`)
Pure, deterministic. Input: raw `list[Evidence]` from agents + which agents were unavailable. Output: a `GateResult`:
```
GateResult:
  trusted:        list[Evidence]      # fresh, in-scope, passed
  excluded:       list[Evidence]      # stale/invalid/malformed
  excluded_ids:   list[str]
  gate_notes:     list[str]           # human-readable reasons
  agents_reporting / agents_unavailable
  missing_required: list[str]         # required signals absent OR all excluded
```
Rules:
1. **Freshness** — recompute `age_seconds` from `timestamp` vs now; classify `fresh <120s`, `stale 120–300s`, `invalid >300s` (thresholds from `config`).
2. **Exclusion** — `stale` and `invalid` evidence is dropped from the trusted set used for safety-critical decisions (note in `gate_notes`).
3. **Provenance** — each signal must come from its *authorized* source (Agent A signals from `agent_a`, etc.). Wrong-source evidence excluded.
4. **Completeness** — using `policy.required_signals()`, flag any required signal missing or fully excluded → `missing_required`.

### 3.3 Policy — `policy.py` (deterministic; OPA seam)
Separates *what is allowed / what matters* from *what should happen*. Cold-chain policy pack:
- Cargo-temp bands: target `2–6°C`, warn `>8`, critical `>10`.
- Contradiction hint: `cooling_status == ON` **and** `cargo_temperature` rising/high → physically inconsistent → strong risk signal.
- `required_signals()` for a valid `AUTO_OPTIMIZE`: `cargo_temperature`, `cooling_status`, `ambient_temperature` (both agents must contribute).
- Freshness thresholds live here too (single source, injected into gate).
> Production: this file becomes an OPA/rego policy bundle. Interface stays the same.

### 3.4 Decision — Confidence (`confidence.py`) + Controller (`controller.py`)
**Confidence (computed in code, never by LLM):**
```
expected     = policy.expected_signal_count()        # signals a healthy fleet emits
contradicted = 2 if matrix.contradiction_detected else 0   # the inconsistent pair
corroborating = max(0, len(gate.trusted) - contradicted)
confidence   = round(corroborating / expected, 2) if expected else 0.0
```
The denominator is the FIXED expected signal count (not the trusted count), so a killed agent or excluded stale signal genuinely lowers confidence instead of cancelling out. Documented and unit-tested with fixed vectors.

**Controller — deterministic 3-state machine (first match wins):**
| # | Condition | State | Action |
|---|---|---|---|
| 1 | any agent unavailable | `INSUFFICIENT_DATA` | none |
| 2 | `critic_rejected` (schema fail / corrupt) | `INSUFFICIENT_DATA` | none |
| 3 | `missing_required` non-empty | `INSUFFICIENT_DATA` | none |
| 4 | `risk_level == HIGH` **or** `contradiction_detected` | `CRITICAL_HALT` | **request escalation action** |
| 5 | otherwise | `AUTO_OPTIMIZE` | none |

The Controller is the **only** component that may call the Action Gateway, and only on `CRITICAL_HALT`.

### 3.5 Authority — Action Gateway (`actions.py`, Layer 2)
- Agents and Critic hold **no reference** to this module (enforced by construction + `test_isolation.py`).
- Controller calls `gateway.request(action_type, decision_ctx)`. The gateway:
  1. Creates an `ActionRequest` (`PENDING_APPROVAL`) with a **tier** from policy:
     - `AUTO` tier (e.g. *create escalation record / notify ops*) → may auto-execute + audit.
     - `HUMAN` tier (e.g. *halt automation*) → stays `PENDING_APPROVAL` until a human approves.
  2. `approve(id, approver)` → `APPROVED` → `execute()` → for the hackathon, "execute" = write an immutable **escalation record** (nothing touches a real fleet system). `reject(id, approver, reason)` → `REJECTED`.
- Every transition is appended to the audit log. Nothing is ever hard-deleted.
> `[FUTURE]` unbuilt seam: `execute()` would route to a real Action Gateway calling fleet systems behind scoped credentials.

---

## 4. Orchestration pipeline (`pipeline.py`)

`run(run_id, vehicle_id) -> ControllerDecision`:
1. `agent_a.observe()` / `agent_b.observe()` — catch `AgentUnavailable`, record unavailable agents.
2. Persist raw evidence (append-only).
3. `gate.evaluate(evidence, unavailable)` → `GateResult`.
4. `critic.assess(gate.trusted)` → `RiskMatrix` **or** rejection (validation error / corrupt switch).
5. `confidence.compute(gate, matrix)`.
6. `controller.decide(gate, matrix, critic_rejected, confidence)` → state + reason.
7. On `CRITICAL_HALT`: `gateway.request(...)` → `escalation_id`.
8. Build `DecisionTrace` + `ControllerDecision`; persist decision; append audit record.
9. Push to any connected dashboard (WebSocket/SSE) and return.

Deterministic, synchronous, easy to reason about and test. No graph framework (per PRD §11.1).

---

## 5. API surface (`main.py`)

**Core**
- `POST /runs` — run a full evaluation on current world → `ControllerDecision` (the primary demo call).
- `GET  /decisions/{run_id}` — latest decision + trace.
- `GET  /runs/{run_id}` — full trace (evidence snapshot, excluded, gate notes).
- `POST /evidence` — external evidence ingestion (seam; validates + gates like internal).
- `GET  /audit` — recent append-only audit records.

**Demo triggers**
- `POST /simulate/scenario` `{name}` — `healthy` | `compound_risk` | …
- `POST /simulate/kill-agent` `{agent, disabled}` — Live failure #1.
- `POST /simulate/corrupt-llm` — Live failure #2 (one-shot).
- `POST /simulate/stale-signal` `{signal}` — stale-exclusion (stretch).
- `POST /simulate/reset` — back to healthy.

**Layer 2 — Action Gateway**
- `GET  /actions/pending` — escalations awaiting human approval.
- `GET  /actions/{id}` — one action + its audit trail.
- `POST /actions/{id}/approve` `{approver}`.
- `POST /actions/{id}/reject` `{approver, reason}`.

**Live**
- `WS /ws` (or `GET /events` SSE) — push each new decision to the dashboard.

> `[FUTURE]` named-but-unbuilt: `POST /policies`, `GET /agents`, `POST /actions/request` routing through a production gateway.

---

## 6. Persistence (`store.py`, SQLite)

WAL-mode SQLite, thin repository (stdlib `sqlite3`, no ORM needed). **Append-only** tables:
- `evidence(evidence_id PK, run_id, …, created_at)`
- `decisions(run_id PK, controller_state, confidence, critic_rejected, risk_json, trace_json, escalation_id, created_at)`
- `audit(id PK, ts, run_id, event_type, payload_json)` — never updated, never deleted.
- `actions(action_id PK, run_id, action_type, tier, status, approver, reason, created_at, updated_at)` + `action_events` for transitions.

Enables the `[FUTURE]` **replay** feature cheaply (all inputs+outputs are stored) and survives a mid-demo restart.

**Concurrency note (found by fuzzing, since fixed):** the Store shares one `sqlite3.Connection` across threads. Every method that touches it — reads included — must serialize through the same `threading.Lock`. An earlier version locked writes only; concurrent-request fuzzing (`scripts/fuzz_api.py`) reliably reproduced reads racing writes and corrupting cursor state (`TypeError`/`IndexError`/`InterfaceError`). Regression-guarded by `tests/test_store.py::test_concurrent_reads_and_writes_never_crash_or_corrupt`.

---

## 7. Build phases (dependency-ordered, each ends green)

Each phase is independently testable; run `pytest` after each.

- **Phase 0 — Foundations.** `config.py`, `store.py` (schema + repo), `audit.py`, `requirements.txt`, `.env.example`. Tidy `agents.py` (normalize `observe()` signatures; `cooling_status` unit).
- **Phase 1 — Trust Gate + Policy.** `policy.py`, `gate.py`. `test_policy.py`, `test_gate.py` (fresh/stale/invalid classification, exclusion, wrong-source, missing-required). Pure, no LLM.
- **Phase 2 — Critic.** `critic.py`: `CriticBackend` protocol, `MockCritic`, `OpenRouterCritic`, strict `RiskMatrix` validation, corruption injection. `test_critic_validation.py` (valid → matrix; malformed/extra-field/non-JSON → rejected). No network in tests.
- **Phase 3 — Confidence + Controller.** `confidence.py`, `controller.py`. `test_confidence.py` (fixed vectors), `test_controller.py` (full decision table).
- **Phase 4 — Action Gateway (Layer 2).** `actions.py`: request/approve/reject/execute, tiers, audit. `test_actions.py` + `test_isolation.py` (agents/critic have **no** callable path to actions; the "unauthorized action attempt" demo moment).
- **Phase 5 — Pipeline.** `pipeline.py`. `test_pipeline_scenarios.py`: healthy→`AUTO_OPTIMIZE`, compound→`CRITICAL_HALT`+escalation, kill-agent→`INSUFFICIENT_DATA`, corrupt→`INSUFFICIENT_DATA`, stale→exclusion.
- **Phase 6 — API.** `main.py` + routers + WS/SSE. `test_api.py` (httpx TestClient over every endpoint + the demo triggers).
- **Phase 7 — Frontend.** Vite React TS dashboard: evidence panels (A/B), Critic reasoning + contradiction flag + confidence, color-coded Controller state, "why this decision?" trace, pending-actions approval panel, demo-trigger buttons. Live updates via WS/polling.
- **Phase 8 — Demo hardening.** `scripts/demo.py` scripted rehearsal, seed data, README run instructions, record a backup clip. Rehearse the §9 demo 3× with a timer.

---

## 8. Testing strategy (what makes it "good, not MVP")

- **Determinism:** gate, policy, confidence, controller are pure functions with table-driven tests — no flakiness.
- **The harness guarantees are tests, not claims:**
  - `test_isolation.py`: asserts Agent A cannot reach environment data; Critic signature takes only `list[Evidence]`; no agent/critic object exposes an action callable.
  - `test_critic_validation.py`: no LLM output reaches the controller without passing `RiskMatrix` validation.
- **Failure paths are first-class:** killed agent, corrupt critic, stale exclusion each have a scenario test.
- CI-ready: single `pytest` run, all green, no network required (mock critic).

---

## 9. Demo plan (unchanged from PRD §9, now backed by real endpoints)

1. Healthy → `AUTO_OPTIMIZE`.
2. `POST /simulate/scenario {compound_risk}` → contradiction flagged → `CRITICAL_HALT` + confidence + a **pending escalation** appears.
3. Approve the escalation in the dashboard (Layer 2 human-in-the-loop) → audit trail shows the full chain.
4. `POST /simulate/kill-agent` → `INSUFFICIENT_DATA`, system stays up.
5. `POST /simulate/corrupt-llm` → schema rejection → `INSUFFICIENT_DATA`.
6. (If time) stale-signal exclusion; unauthorized-action attempt (no callable path).
7. Close line: *"We're not making the AI impossible to fail. We're building the system around it so that when it fails, the operation doesn't."*

---

## 10. Success criteria (from PRD §10, made testable)

- [ ] Every demo scene runs live via an endpoint, no code edits.
- [ ] No LLM output reaches the Controller without `RiskMatrix` validation — *proven by test*.
- [ ] No agent/Critic has a code path to execute a fleet action — *proven by test*.
- [ ] A judge can follow the decision chain from the dashboard alone.
- [ ] `pytest` green with zero network dependency.

---

## 11. Open items to confirm with organizers (PRD §15)
- Judging rubric / time limits → final prioritization of Phase 7–8 polish.
- Final model id on OpenRouter (default suggestion: a fast, cheap instruct model; set in `.env`).
- Team role split across phases 1–8.
