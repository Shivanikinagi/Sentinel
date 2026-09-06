# Fleet-Harness — Master Demo

**The complete walkthrough.** 16 chapters, **20 min 46 s** as recorded, covering every page, every
runtime subsystem, every agent, every policy pack, every simulation, every
visualization, and every significant UX flow.

This is the *master* cut. It is deliberately longer than any pitch: it exists so
shorter versions (3-minute hackathon cut, 5-minute technical cut, 10-minute
architecture cut) can be edited **out** of it without re-shooting. See
[Editing this into shorter cuts](#editing-this-into-shorter-cuts).

---

## The thesis the demo argues

> **Intelligence is advisory. Deterministic policy is authoritative.**

Fleet-Harness is not an AI agent; it is a *trust harness*. Every chapter is an
argument for one claim: that an operational system can use a language model
without ever letting the model be the final authority over an action.

The demo is built so a technically sophisticated audience leaves knowing **why**
the architecture exists, not just what it looks like. Concretely, it demonstrates
three refusals that a naive "telemetry → LLM → action" design cannot make:

| Refusal | Enforced by | Chapter |
|---|---|---|
| Refuse untrustworthy **evidence** | `gate.py` — freshness, provenance, completeness, normalization | 4, 10 |
| Refuse untrustworthy **reasoning** | `critic.py` strict `RiskMatrix` validation + `verifier.py` | 8, 10 |
| Refuse to grant the model **authority** | `controller.py` state machine + `actions.py` gateway + `security.py` | 9, 12, 15 |

---

## How to run it

```bash
python demo/create_master_demo.py
```

That single command starts the backend and the frontend, waits for both to be
ready, resets the world to a documented baseline, then drives the whole
walkthrough through a real Chromium browser — recording video, capturing a still
per chapter, and writing captions timed to the actual elapsed run.

| Flag | Effect |
|---|---|
| *(none)* | Full run, boots both servers, records video |
| `--headed` | Show the browser while it drives |
| `--speed 8` | Fast rehearsal (validates every selector in ~6 min) |
| `--no-servers` | Attach to a backend/frontend that are already running |
| `--no-video` | Skip the recording |
| `--chapters 8,9` | Run only those chapters |
| `--dry-run` | Print the plan and write planned captions; no browser |

Outputs land in `demo/`: `automation.log`, `captions.srt`, `screenshots/*.png`,
`video/*.webm`.

The backend runs with **no API key**. A deterministic `MockCritic` stands in for
the model, so the walkthrough is reproducible and never depends on the network.
Set `OPENROUTER_API_KEY` in `backend/.env` to run the same script against a real
model — every guarantee shown is enforced on the harness side, not the model side.

---

## Architecture under demonstration

```
Planner → Supervisor( agents → Trust Gate [4 sub-stages] → Correlation →
          Risk Assessment Engine [retry + circuit breaker] → Verifier →
          Deterministic Controller )
        → Harness (persist evidence + decision, request action on CRITICAL_HALT)
        → Store / Action Gateway / Audit
```

Every box maps to one module, and every module is shown on screen at least once:

| Layer | Module | Responsibility | Shown in |
|---|---|---|---|
| Runtime | `supervisor.py` | Launch agents, time stages, retry, build trace | Ch 2, 7 |
| Runtime | `run_state.py` | One `RunState` per run, read/written by every stage | Ch 2, 7 |
| Runtime | `planner.py` | Which agents run, and whether in parallel | Ch 2, 4 |
| Runtime | `retry_engine.py` | Bounded retry *inside* a run | Ch 2, 10 |
| Runtime | `circuit_breaker.py` | Whether to attempt the call at all, *across* runs | Ch 10 |
| Runtime | `events.py` | Typed event bus; Audit is one subscriber | Ch 7 |
| Runtime | `memory.py` | Per-vehicle, per-signal trend + reliability score | Ch 7 |
| Runtime | `metrics.py` | Aggregates over everything persisted | Ch 7 |
| Runtime | `incidents.py` | Past halts joined with how they resolved | Ch 7, 13 |
| Runtime | `audit.py` / `store.py` | Append-only log, durable SQLite store | Ch 9, 13 |
| Intelligence | `agents.py` | Two observers with code-enforced disjoint scopes | Ch 4, 12 |
| Intelligence | `critic.py` | The only LLM in the path; no tools, no authority | Ch 4, 8, 10 |
| Intelligence | `tools.py` | Per-agent scoped tool registry | Ch 12 |
| Evidence | `gate.py` | Freshness / provenance / completeness / normalization | Ch 4, 10 |
| Evidence | `correlation.py` | Deterministic physical conflicts, pre-LLM | Ch 4, 8 |
| Evidence | `verifier.py` | 3 checks on the model's output vs. its evidence | Ch 4, 8 |
| Policy | `policy.py` / `policy_packs.py` | Swappable domain packs | Ch 11 |
| Decision | `controller.py` | 3-state machine, first match wins | Ch 8, 15 |
| Decision | `confidence.py` | Confidence + composite, computed in code | Ch 7, 15 |
| Authority | `actions.py` | Action Gateway, HUMAN-tier approval | Ch 9, 15 |
| Authority | `security.py` | Live red-team probe of the agent → action path | Ch 12 |

---

## Chapter-by-chapter walkthrough

Each heading carries the chapter's start time in the recorded run, then its narration length. Recorded end to end: **20:46**, 155 narration lines, zero failed steps (`automation.log`).

### Chapter 1 — The Problem — 00:05 (0:57) · `/`

**On screen:** Dashboard at rest; the *LLM Zero Decision Authority* badge; the
critic-backend badge.

**Argument.** Fleet-Harness is a decision-control layer, not an agent. The asset
is `TRUCK-042`, a refrigerated truck whose cargo spoils outside 2–6 °C. The naive
design — telemetry into a model, model decides — fails three ways: it trusts any
data, it trusts any model output, and it grants the model authority. The harness
separates those three concerns into different modules and never lets them
recombine.

**Proves:** framing. **Backing:** `README.md`, `config.py` (`use_mock_critic`).

---

### Chapter 2 — Architecture — 01:03 (1:26) · `/runtime`, `/pipeline`

**On screen:** the Harness Runtime diagram (8 component tiles, each a real
module), the flow-order line beneath it, then the five Architecture Layers on the
Pipeline page.

**Argument.** Walks every runtime tile: Supervisor, State Manager (`RunState`),
Scheduler (`Planner`), Retry Engine, Policy Engine, Execution Trace, Memory,
Audit. Names the Retry Engine / Circuit Breaker distinction explicitly — retry is
*within* a run, the breaker is *across* runs. Ends on the five layers:
Intelligence, Evidence, Policy, Decision, Authority.

**Proves:** the layers exist as separate modules, not as sections of one prompt.
**Backing:** `supervisor.py`, `run_state.py`, `planner.py`, `retry_engine.py`,
`policy_packs.py`, `memory.py`, `audit.py`.

---

### Chapter 3 — The Dashboard — 02:31 (1:21) · `/`

**On screen, in order:** session top line → Harness Trust Score → "What Could
Have Gone Wrong" counterfactual → 5-layer pipeline strip → failure injection bar
→ Live Execution panel → Recent Events feed → decision trace timeline → evidence
provenance → controller banner + approvals queue → speed selector → Simple /
Technical toggle.

**Argument.** Every widget is explained. Two are explicitly framed as
non-measurements: the counterfactual card's loss figure is illustrative, and the
speed selector only changes the dashboard's poll interval.

**Proves:** the operator surface is a live view of one real run, not a mock.
**Backing:** `missioncontrol.tsx`, `components/PipelineVisualizer.tsx`,
`components/ProvenanceCard.tsx`, `humanize.ts` (the Simple/Technical layer).

---

### Chapter 4 — A Healthy Run — 03:54 (1:39) · `/`

**On screen:** Healthy scene → Run check → the Live Execution flow animates
agents → gate → risk → decision → gateway; then the trace timeline with the four
Trust Gate sub-stages expanded; then the controller banner.

**Argument.** The full execution order, narrated against what is actually
happening: Planner dispatches both observers in parallel *because their scopes are
provably disjoint*; 9 signals collected (5 truck, 4 environment); the gate's four
sub-stages (Schema Validator, Freshness Checker, Provenance Checker, Evidence
Normalizer); the Correlation Engine's three deterministic physical checks *before*
the model reasons; the Risk Assessment Engine reasoning over structured evidence
only; the Verifier's three checks; the Controller deciding.

**Result:** `AUTO_OPTIMIZE`, **confidence 100 %**, whole chain in single-digit
milliseconds.

**Proves:** parallel agents, the gate does real work, the LLM is one stage of
seven and not the decision. **Backing:** `planner.py`, `gate.py`,
`correlation.py`, `critic.py`, `verifier.py`, `controller.py`;
`tests/test_pipeline_scenarios.py`, `tests/test_gate.py`.

---

### Chapter 5 — Vehicle Explorer — 05:38 (0:48) · `/vehicle`

**On screen:** four headline stats (Trust Gate / Evidence Freshness / Confidence
/ Policy Pack), confidence history sparkline, live telemetry grid, the two
per-agent evidence panels, the AI Risk Assessment panel.

**Argument.** The page deliberately shows *raw world state* and *gated evidence*
as two separate things — that visual separation is the point, because the gate is
what happens between them. Every reading carries freshness status and source
agent; exclusions are shown as exclusions.

**Proves:** telemetry, world state, trust status, confidence, freshness and the
active policy pack, per asset. **Backing:** `world.py`, `agents.py`, `gate.py`.

---

### Chapter 6 — The Pipeline Page — 06:28 (0:22) · `/pipeline`

**On screen:** the 5-layer strip, the pipeline stepper for the current run, the
gate-note reasons, the Architecture Layers list.

**Argument.** The same run pinned against the architecture: sensors reporting →
evidence trusted vs. ignored → AI review → decision → whether anything went for
approval, with every gate exclusion written out in plain language (and the raw
note underneath it in Technical mode).

**Proves:** every stage of the pipeline, end to end, for one concrete run.

---

### Chapter 7 — Runtime Deep Dive — 06:51 (2:08) · `/runtime`

**On screen:** Supervisor Console → failure counters → Harness Metrics →
Confidence Computation → composite trust score → Signal Trend (Memory) → World
State → Decision Certificate → Incident Memory.

**Argument.** Reads the runtime's *live state* rather than the diagram.

- **Supervisor Console** — a log of what the Supervisor actually did, built from
  `decision_chain` / `retries`; the counters below it are agents launched, agent
  failures, retries, recovered.
- **Harness Metrics** — aggregated server-side over everything persisted, never
  in-memory counters.
- **Event Bus** — named explicitly here because it has no diagram tile: every
  stage *publishes a typed event* instead of calling Audit directly; Audit is one
  subscriber; the vocabulary is fixed at 16 event types; the bus keeps its own
  ring buffer.
- **Confidence Computation** — the arithmetic, then the five-factor composite.
- **Memory** — a signal across the vehicle's past runs, with direction and delta.
  The signal selector is switched live to `ambient_temperature`.
- **Decision Certificate** — five checks, each derived from a real decision field.
- **Incident Memory** — introduced here as a *different subsystem from Memory*
  (drift vs. "what went wrong and was it resolved"), and honestly shown empty,
  because nothing has failed yet. Chapter 13 comes back to it.

**Proves:** Supervisor, RunState, Planner, Retry Engine, Event Bus, Memory,
Metrics, Audit — the full runtime requirement list.
**Backing:** `supervisor.py`, `metrics.py`, `events.py`, `confidence.py`,
`memory.py`, `incidents.py`; `tests/test_harness_runtime.py`.

---

### Chapter 8 — Contradictory Evidence — 09:03 (1:41) · `/`

**On screen:** Risk Anomaly scene → Run check → trace timeline → controller
banner → Decision Explainer modal.

**Argument.** The world changes: cooling reports **ON** while cargo is **11.5 °C**
(nearly double the top of the band), ambient **41 °C**, dwell **37 minutes**.
Those two facts cannot both be true.

1. **Correlation** catches it deterministically, *before* the model reasons —
   "cooling ON but cargo above safe max", plus thermal dwell risk.
2. **The Risk Assessment Engine** reasons over the same evidence: `HIGH`,
   `contradiction_detected: true`, four risk factors.
3. **The Verifier** checks that assessment *against its evidence*: HIGH is backed
   by factors, every factor maps to a present signal, the contradiction has enough
   evidence. All three pass.
4. **Confidence falls 100 % → 78 %** — (9 trusted − 2 contradiction penalty) ÷ 9.
5. **The Controller** — three states, first match wins, in the order: agents down,
   output rejected, required evidence missing, confirmed risk, healthy — reaches
   rule 4 and returns `CRITICAL_HALT`. It is the only component permitted to
   request an action.
6. The **Decision Explainer** shows the whole chain in one panel; every claim in it
   is a stored field, not a browser-side re-derivation.

**Proves:** contradictory evidence, critic reasoning, confidence changes,
deterministic policy. **Backing:** `correlation.py`, `critic.py`, `verifier.py`,
`controller.py`, `confidence.py`; `tests/test_controller.py`,
`tests/test_confidence.py`.

---

### Chapter 9 — Human Approval — 10:51 (0:53) · `/`

**On screen:** the pending action card → Approve → executed state.

**Argument.** Halting automation is a **HUMAN-tier** action. It does not execute;
it opens for approval and waits, and nothing inside the system can move it
forward. On approval the gateway transitions `PENDING_APPROVAL → APPROVED →
EXECUTED` and creates an immutable escalation record; three rows land on the
action's own event log, each with an actor and timestamp. Rejection with a reason
is recorded just as durably — a decision not to act is still a decision.

**Proves:** human approval, escalation, the append-only trail.
**Backing:** `actions.py` (`TIER_FOR_ACTION`), `audit.py`, `store.py`;
`tests/test_actions.py`.

---

### Chapter 10 — The Failure Matrix — 11:46 (2:25) · `/simulation`, `/`, `/runtime`

Returns to normal conditions first, so each failure is isolated. Every control
hits a real endpoint.

| # | Injection | Endpoint | Observed result |
|---|---|---|---|
| 1 | Kill Environment Agent | `POST /simulate/kill-agent` | `INSUFFICIENT_DATA`, **56 %** (5 of 9 signals) — controller rule 1 |
| 2 | Corrupt model output | `POST /simulate/corrupt-llm` | 2 validation errors → rejected, `INSUFFICIENT_DATA`, **confidence still 100 %** — rule 2 |
| 3 | Stale telemetry | `POST /simulate/stale-signal` | reading backdated 4 min → excluded → `INSUFFICIENT_DATA`, **89 %** — rule 3 |
| 4 | Network blip | `POST /simulate/transient-error` | `retries: 1`, recovered inside the same run; retry row + RECOVERED badge in the trace |
| 5 | Circuit breaker | `POST /simulate/circuit-breaker` | breaker OPEN → call not attempted at all → immediate degrade; `circuit_breaker_open: true` on that run; closes again after cooldown |
| 6 | Sensor drift | `POST /simulate/sensor-drift` | cargo forced to 14.5 °C |
| 7 | Emergency override | `POST /simulate/emergency-override` | worst case: 15 °C with cooling still reporting ON |

**The point made about #2 is the important one:** confidence stays at 100 %
because *confidence measures evidence completeness*, and the evidence was
complete. The model failing is a separate axis, and the Controller refuses on that
axis independently. Two orthogonal guards, not one blended score.

The System Indicators panel is shown tracking all of it live.

**Proves:** every simulation the app offers; graceful degradation without a
crash or a restart. **Backing:** `main.py` simulate endpoints, `retry_engine.py`,
`circuit_breaker.py`; `tests/test_verifier_and_resilience.py`,
`tests/test_critic_validation.py`.

---

### Chapter 11 — Policy Packs — 14:30 (1:11) · `/runtime`, `/`

**On screen:** the Policy Engine card → select **Tyre Safety** → run the *same
world state* → back to the confidence arithmetic → switch back to Cold Chain.

**Argument.** Nothing in the gate, correlation engine, verifier or controller
knows what cold chain *is*. The domain lives in a policy pack.

- **Cold Chain** requires `cargo_temperature`, `cooling_status`,
  `ambient_temperature`; expects **9** signals.
- **Tyre Safety** requires `tyre_pressure`, `tyre_temperature`, `vehicle_speed`;
  expects **5**.

Running the identical world under Tyre Safety: cargo temperature, cooling status,
weather severity and dwell are now **excluded as unknown signals** — they are not
in this policy's vocabulary at all. The expected-signal denominator moves 9 → 5,
so the confidence arithmetic changes underneath. The reasoner switches to tyre
logic: the contradiction it hunts is underinflation + heat, not cooling vs. cargo.

**The telemetry that produced `CRITICAL_HALT` under Cold Chain produces
`AUTO_OPTIMIZE` under Tyre Safety** — because policy, not the model, decides what
counts as evidence and what counts as risk. Zero code changes in gate,
correlation, risk engine or controller.

**Proves:** the harness is domain-independent. **Backing:** `policy_packs.py`,
`GET|POST /policy/packs|active`; `tests/test_policy.py`.

---

### Chapter 12 — Isolation — 15:50 (1:05) · `/runtime`, `/simulation`

**On screen:** Isolation Proof card → "Try: Vehicle → Environment API" → the
red-team Security Check probe.

**Argument.** Two live, unstaged attempts:

1. The **Vehicle Agent genuinely calls** the Environment Agent's tool. The Tool
   Registry denies it — scoped access, checked at call time
   (`ToolAccessDeniedError`).
2. The **red-team probe** inspects the live agent object for seven action-shaped
   attributes, then parses the `agents` module's import graph to see whether it
   can even *reach* the action gateway. **8 attempts, all blocked** — not by a
   permission check that could be misconfigured, but by the absence of any
   reference at all. `agents.py` does not import `actions.py`; neither does
   `critic.py`.

Enforced by tests, not convention: `tests/test_isolation.py` fails the build the
moment anyone wires an action onto an agent. **98 tests** cover the gate, policy,
critic validation, confidence, the controller table, the gateway, the HTTP
surface and the runtime, plus property-based fuzzing over random inputs.

**Proves:** why agents cannot directly execute actions.
**Backing:** `security.py`, `tools.py`, `tests/test_isolation.py`.

---

### Chapter 13 — Replay and Audit — 16:56 (1:02) · `/audit`, `/runtime`

**On screen:** audit trail → filter by `decision_made` → search "halt" → select a
record → the reconstructed decision → "Replay Incident" on the trace → Incident
Memory, now populated.

**Argument.** Every run is durably persisted: the decision, its full evidence
snapshot, gate notes, verifier result, timed execution trace. The trail is
append-only; nothing in it is rewritten. Selecting any record that carries a
`run_id` reconstructs that decision *out of storage* — stepper, state, reason, and
the reasoning summary current at the time. The trace itself replays stage by
stage, paced by the durations that were actually recorded. Incident Memory has
filled in: the halts we caused, joined with how each action resolved and by whom.

**This is what makes an incident reviewable by someone who was not in the room** —
not a log line saying the system halted, but the exact evidence, the exact
assessment, the exact rule that fired, and who approved what.

**Proves:** replay, the immutable audit trail, incident memory.
**Backing:** `store.py`, `audit.py`, `incidents.py`, `GET /decisions/{run_id}`;
`tests/test_store.py`.

---

### Chapter 14 — Analytics and Configuration — 18:01 (0:43) · `/analytics`, `/settings`

**On screen:** four stat cards → Decision Funnel → confidence sparkline →
decision distribution bars → four health donuts → Settings.

**Argument.** Every chart explained. The **Decision Funnel** is the load-bearing
one: runs → evidence complete → risk assessed → verifier passed → automation
continued. *The drop-off between stages is exactly where the harness refused to
proceed; every step down is a decision not taken.* Settings shows which reasoning
backend is live, the active scenario, and the API base being polled.

**Proves:** every visualization. **Backing:** `charts.tsx`,
`components/DecisionFunnel.tsx`, `metrics.py`.

---

### Chapter 15 — Confidence and Authority — 18:46 (1:04) · `/runtime`

The two ideas the whole design rests on, stated precisely.

**Confidence.** A measure of *evidence*, computed in code, with a **fixed
denominator**:

```
expected      = signals a healthy fleet produces      (9 for cold_chain)
contradicted  = 2 if the Critic flagged a contradiction
corroborating = max(0, trusted_count - contradicted)
confidence    = corroborating / expected
```

If the denominator were "signals you happened to receive", losing an agent would
leave you at 100 % confidence in a smaller picture. It is not. So a killed agent,
an excluded stale reading, or a detected contradiction genuinely lowers the
number — the only safe behaviour. The model is *forbidden* from reporting
confidence: the key is not in the schema (`extra="forbid"`) and output carrying it
is rejected. On top of that sits the composite: `evidence quality × verifier score
× gate cleanliness × policy compliance × historical reliability`, each factor
measured elsewhere in the system.

**Authority.** The model's output is an *input to* a decision, never the decision.
It is schema-validated, verified against its evidence, then consumed by a state
machine you can read in about forty lines. The Controller is the only component
permitted to request an action, and only in one of its three states. Halting
automation is HUMAN-tier, so it opens for approval and waits.

**Which means: if the model is unavailable, malformed, contradictory or simply
wrong, the worst outcome this system can reach is a refusal to act.**

**Backing:** `confidence.py`, `controller.py`, `actions.py`, `schemas.py`.

---

### Chapter 16 — Closing — 19:51 (0:53) · `/pipeline`, `/`

Summarises the five layers, opens the app's own built-in Presenter Guide (which
maps each scene to the module that guarantees it), and closes on:

> **Agents investigate.**
> **The Critic challenges.**
> **Deterministic policy decides.**

---

## Coverage matrix

Every requirement, and where it is demonstrated.

### Pages (7 + Settings)

| Page | Route | Chapters |
|---|---|---|
| Dashboard | `/` | 1, 3, 4, 8, 9, 10, 11, 16 |
| Harness Runtime | `/runtime` | 2, 7, 10, 11, 12, 13, 15 |
| Vehicle Explorer | `/vehicle` | 5 |
| Harness Pipeline | `/pipeline` | 2, 6, 16 |
| Simulation Lab | `/simulation` | 10, 12 |
| Audit Logs | `/audit` | 13 |
| Analytics | `/analytics` | 14 |
| Settings | `/settings` | 14 |

### Runtime subsystems

Supervisor (2, 7) · RunState (2, 7) · Planner (2, 4) · Retry Engine (2, 10) ·
Circuit Breaker (10) · Event Bus (7) · Memory (7) · Metrics (7) ·
Incident Memory (7, 13) · Audit (9, 13) · Execution Trace (3, 4, 13) ·
Store / replay (13)

### AI components

Vehicle Agent (4, 5, 12) · Environment Agent (4, 5, 10) · Risk Assessment Engine
(4, 8, 10) · Verifier (4, 8) · Trust Gate (4, 5, 10) · Correlation Engine (4, 8) ·
Decision Authority / Controller (4, 8, 15) · Policy Engine + packs (11) ·
Tool Registry (12)

### Simulations (all 10)

`scenario:healthy` (4, 10) · `scenario:compound_risk` (8) · `kill-agent` (10) ·
`corrupt-llm` (10) · `stale-signal` (10) · `transient-error` (10) ·
`circuit-breaker` (10) · `sensor-drift` (10) · `emergency-override` (10) ·
`unauthorized-tool` (12) · `unauthorized-action` (12) · `reset` (baseline)

### Visualizations

Harness Trust Score donut (3) · Guardrail counterfactual (3) · 5-layer pipeline
strip (3, 6) · Live Execution flow (3, 4) · Live event feed (3) · Trace timeline
+ gate sub-stage chips (4, 13) · Provenance grid (3) · Supervisor console (7) ·
Metrics grid (7) · Confidence arithmetic + composite bars (7, 15) · Signal trend
sparkline (7) · World state grid (7) · Decision certificate (7) · Incident list
(13) · Decision funnel (14) · Confidence sparkline (14) · Distribution bars (14) ·
Health donuts (14)

### UX flows

Run check (4) · Scene switching (4, 8) · Failure injection bar (10) ·
Approve action (9) · Reject with reason (9, narrated; dialog handled by the
script) · Simple/Technical toggle (3) · Poll-speed selector (3) · Decision
Explainer modal (8) · Presenter Guide drawer (16) · Policy pack selection (11) ·
Trend signal selector (7) · Audit filter + search + row select (13) ·
Replay Incident (13) · Isolation probe buttons (12)

### API surface exercised

`GET /health` · `POST /runs[?policy_pack=]` · `GET /decisions` ·
`GET /decisions/{run_id}` · `GET /state` · `GET /audit` · `GET /actions/pending` ·
`POST /actions/{id}/approve` · `POST /actions/{id}/reject` · `GET /metrics` ·
`GET|POST /policy/packs|active` · `GET /vehicles/{id}/trend` · `GET /incidents` ·
`GET /events/types` · `GET /events/recent` · `GET /tools` · all `POST /simulate/*`

---

## Verified numbers

Every figure the narration quotes, and where it comes from. These were read back
out of the running system during the recorded run (see `automation.log`).

| Scenario | State | Confidence | Why |
|---|---|---|---|
| Healthy | `AUTO_OPTIMIZE` | **100 %** | 9 / 9 trusted, no contradiction |
| Compound risk | `CRITICAL_HALT` | **78 %** | (9 − 2 contradiction) ÷ 9 |
| Environment Agent killed | `INSUFFICIENT_DATA` | **56 %** | 5 of 9 signals survived |
| Corrupt model output | `INSUFFICIENT_DATA` | **100 %** | evidence complete; refused on the *reasoning* axis |
| Stale cargo reading | `INSUFFICIENT_DATA` | **89 %** | 8 of 9 trusted; required signal excluded |
| Network blip | recovers | — | `retries: 1`, same run |
| Breaker open | `INSUFFICIENT_DATA` | — | call not attempted; `circuit_breaker_open: true` |
| Same world, Tyre Safety | `AUTO_OPTIMIZE` | **100 %** | 5 / 5 tyre signals; 4 cold-chain signals excluded as unknown |

Composite trust score on the halt run: `0.78 × 1.0 × 1.0 × 0.5 × 1.0 = 0.39`
(policy compliance loses 0.25 per physical conflict, and correlation found two).

Test suite: **98 passed**.

Recorded pass: **20 min 46 s**, 16 chapters, 155 narration lines, 43 stills, 0 recoverable step failures.

---

## The 3-minute cut — already built

The short version is not an edit of this recording; it is **generated the same
way, from its own script**, so it is narrated, captioned and re-runnable rather
than trimmed by hand:

```bash
python create_demo.py          # -> demo/ColdChain-Harness-Demo.mp4
```

| | |
|---|---|
| **Output** | `demo/ColdChain-Harness-Demo.mp4` — 1920×1080, H.264 + AAC |
| **Length** | ~3¼ minutes, title card + 3 acts + end card |
| **Narration** | Synthesised offline with Windows SAPI, no API key, no network |
| **Captions** | Burned in, generated from the same beat table as the audio |
| **Log** | `demo/video_pipeline.log` |

Three acts, chosen so each carries one of the three refusals:

| Act | Beats | Shows | Refusal |
|---|---|---|---|
| **1 — A normal shipment** | 7 | Isolated agents → Trust Gate's four sub-stages → risk assessment → `AUTO_OPTIMIZE` at 100 % | evidence |
| **2 — Contradictory evidence** | 11 | Cooling ON at 11.5 °C → correlation catches it pre-LLM → critic finds it → verifier checks it → confidence 100 → 78 % → `CRITICAL_HALT` | reasoning |
| **3 — Authority** | 6 | Human-tier approval, escalation record, then two live isolation probes — agent → tool denied, and 8/8 agent → action paths blocked | authority |

The pipeline is four stages: synthesise the narration and **measure each clip**,
start the real servers, drive the real UI with Playwright while recording, then
assemble with ffmpeg — cards, cross-fades, narration mixed onto the timeline,
captions burned in. Narration length is what paces the capture, so there is no
dead air to strip afterwards. Flags: `--skip-capture` (re-assemble only),
`--skip-tts`, `--no-servers`, `--headed`, `--keep-build`, `--dry-run`.

---

## Editing this into shorter cuts

If you would rather cut *this* recording than run the short pipeline: the chapter
boundaries are the edit points. Every chapter opens on a title card and ends on a
settled screen, so cuts are clean.

**3-minute hackathon cut** — Ch 1 (first 3 beats) → Ch 4 (healthy run + result) →
Ch 8 (contradiction → halt) → Ch 9 (approve) → Ch 16 (last 3 lines).
The three-refusals story with one demonstration each — the same shape the
generated 3-minute video takes.

**5-minute technical cut** — add Ch 12 (isolation probe) and Ch 11's pack switch.

**10-minute architecture cut** — Ch 1, 2, 4, 7, 8, 9, 11, 12, 15, 16. Drops the
page tour (3, 5, 6, 14) and most of the failure matrix, keeps every architectural
claim.

**"Does it survive failure?" cut** — Ch 10 standalone, plus Ch 15's closing line.
Runs about 3 minutes on its own.

---

## Honest framing (things the narration is careful about)

The demo deliberately does **not** overclaim. Three points where the script is
explicit:

1. **The counterfactual card's loss figure is illustrative**, not a measurement.
   The narration says so out loud (Ch 3).
2. **"Execute" means creating an immutable escalation record.** Nothing touches a
   real fleet system. `actions.py` marks the production gateway as a `[FUTURE]`
   seam.
3. **The reasoner is a deterministic mock by default.** Every guarantee shown is
   enforced on the harness side — schema validation, verification, the gate, the
   controller — so it holds identically against a real model. The demo says this
   in Chapter 1 rather than hiding it.

The topbar's shield counter counts failures injected in the current browser
session; it is a session counter, not a fleet statistic.

---

## Presentation changes made to the app

Four small, presentation-only edits. No business logic, no architecture, no
redesign — three of them are accuracy fixes to text that was already wrong.

| File | Change | Why |
|---|---|---|
| `frontend/src/styles.css` | `html { scroll-behavior: smooth }` (with a `prefers-reduced-motion` opt-out) | Scripted and anchor scrolling glides instead of jumping, which is what makes a recorded walkthrough readable |
| `frontend/src/styles.css` | Entrance animation on `.timeline-step-item` | "Replay Incident" reveals trace rows one at a time; easing them in reads as a deliberate step-through instead of rows popping into existence |
| `frontend/src/components/PresenterGuide.tsx` | Scene 2 label `100%` → **`78%`**; Scene 3 label `0%` → **`44%`**, and the matching script lines | Both were wrong. A contradiction *lowers* confidence to (9−2)÷9 = 78 %; killing the Vehicle Agent leaves 4 of 9 signals = 44 %, not 0 % |
| `frontend/src/FleetDataContext.tsx` | `survivedFailuresCount` seed `4` → `0` | The topbar shield badge is labelled "anomalies survived"; seeding it at 4 made a real session counter look like a fabricated statistic |

The demo overlay — chapter chip, caption bar, spotlight ring — is injected by
`create_master_demo.py` at browser level and is not part of the application.

---

## Related files

| File | What it is |
|---|---|
| `demo/narration.md` | Full narration, word for word, with timecodes |
| `demo/presenter_notes.md` | Speaking notes, cue cards, Q&A, recovery drills |
| `demo/captions.srt` | Captions timed to the recorded run |
| `demo/create_master_demo.py` | The automation that produces all of the above |
| `demo/automation.log` | Timestamped log of the recorded run |
| `create_demo.py` | The 3-minute video pipeline (narrate → serve → capture → assemble) |
| `demo/ColdChain-Harness-Demo.mp4` | The finished 3-minute video |
| `demo/video_pipeline.log` | Timestamped log of the video build |
