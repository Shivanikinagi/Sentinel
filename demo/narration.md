# Narration — Fleet-Harness Master Demo

Full narration, word for word, in delivery order. **16 chapters, 155 lines, ~20 minutes.**

> Generated from the beat table in `create_master_demo.py` — the same table that drives the browser and emits `captions.srt`. The spoken script, the captions and the on-screen actions cannot drift apart.

Timecodes are **measured from the recorded run**. Each line is one caption. Italics are what the browser does while the line is spoken — the narrator talks *over* the click, never after it.

**Delivery:** about 165 words a minute. A full stop is a real pause. The three closing lines get a beat of silence between them.

---

## Chapter 1 — The Problem

*00:05 · Why a harness, and not an agent · 0.95 min*

**00:07**  Fleet-Harness is not an AI agent. It is a trust harness: a decision-control layer between AI reasoning and a real operational action.

**00:17**  The asset is a refrigerated truck, TRUCK-042, carrying cargo that spoils outside a two-to-six degree band.

**00:23**  The obvious design hands the telemetry to a language model and lets it decide. That design fails in three ways.

**00:30**  It trusts whatever data arrives: stale, duplicated, or from the wrong sensor.

**00:35**  It trusts whatever the model says: malformed, ungrounded, or internally contradictory.

**00:39**  And it gives the model authority to change something physical.

**00:43**  Fleet-Harness splits those three concerns into separate modules that never collapse back into one call. Intelligence is advisory, evidence is gated, deterministic policy is authoritative — each boundary enforced in code and backed by a test.

**00:56**  It boots with no API key: a deterministic mock reasoner stands in, so nothing here depends on the network.

---

## Chapter 2 — Architecture

*01:03 · The Harness Runtime and the five layers · 1.43 min*

**01:05**  This is the Harness Runtime. Every box maps to a real backend module.

**01:12**  The Supervisor starts each agent, times every stage, retries the one call that crosses a network boundary, and assembles the execution trace.

**01:20**  The State Manager is RunState: one object per run that every stage reads and writes, instead of variables threaded from function to function.

**01:28**  The Scheduler is the Planner. It decides which agents run, and whether they may run in parallel.

**01:35**  The Retry Engine bounds retries inside one run. The Circuit Breaker is separate: it decides whether to attempt the call at all, across runs.

**01:43**  The Policy Engine selects the active domain pack. The gate, the correlation engine and the reasoner all read from whichever pack is active.

**01:52**  The Execution Trace times every stage, including retries and the four Trust Gate sub-stages.

**01:57**  Memory tracks a signal across a vehicle's past runs, so the harness judges a trend, not a snapshot.

**02:04**  Audit is an append-only log of every meaningful transition.

**02:08**  The line underneath is the real call order: Planner, Supervisor running agents, gate, correlation, risk assessment, verifier, controller — then the Harness, which persists and decides whether to request an action.

**02:19**  The same architecture as five layers, each in its own module: Intelligence, Evidence, Policy, Decision, Authority — never collapsed into one model call. That separation is the product.

---

## Chapter 3 — The Dashboard

*02:31 · Every widget on the operator view · 1.35 min*

**02:33**  The operator's view is a control room, not a KPI wall.

**02:38**  Top line: decisions waiting on a human, vehicles monitored, harness runs this session. The Harness Trust Score beside it composites four measured things — evidence freshness, agent health, schema validity, verifier checks.

**02:49**  Beside it the counterfactual: what an unconstrained model with direct fleet-API access would do with this telemetry. That figure is an illustrative loss, not a measurement.

**02:59**  The five-layer strip is live — each box takes its colour from the run that just executed. Under it, the failure injection bar: every button calls a real endpoint, none is staged.

**03:12**  Live Execution animates the real call order: two agents in parallel, gate, risk assessment, decision authority, action gateway.

**03:19**  Beside it the events feed — the same audit stream the Audit page reads.

**03:24**  Then the decision trace, every stage's duration in milliseconds.

**03:28**  Then provenance: every reading carries a sensor id, a hash of its raw payload, and the transformations applied to it.

**03:36**  At the bottom, the controller banner and the approvals queue — the only place an action is ever released. The speed selector up top changes how often the dashboard polls.

**03:47**  And Simple versus Technical: plain English for an operator, or the internal vocabulary underneath it.

---

## Chapter 4 — A Healthy Run

*03:54 · Agents, gate, correlation, critic, verifier, controller · 1.65 min*

**03:56**  A healthy run, end to end.

**04:00**  Both agents light first, together, then the gate, risk assessment, the decision, the gateway.

**04:10**  The Planner dispatched both observers in parallel because their scopes are provably disjoint: the Vehicle Agent sees only the truck's sensors, the Environment Agent only route and weather.

**04:20**  Nine signals collected — five from the truck, four from the environment.

**04:24**  The Trust Gate ran four sub-stages over them, broken out inside the gate step.

**04:31**  Schema Validator: every reading is a well-formed, typed observation. Freshness Checker: age recomputed from the timestamp, never trusted from a status field — under two minutes fresh, past five minutes invalid.

**04:42**  Provenance Checker: each signal has exactly one authorized source agent. A reading from the wrong agent is excluded even when the value looks fine.

**04:51**  Evidence Normalizer: one trusted reading per signal, the freshest. That is what makes the confidence denominator a real upper bound.

**04:58**  Then Correlation runs deterministic physical checks before the model reasons at all: cooling on while cargo is warm, heat plus long dwell, cargo too cold for the ambient with cooling off.

**05:09**  Only then does the Risk Assessment Engine reason, over structured evidence only. No tools, no world state, no action function.

**05:17**  The Verifier checks the model against its evidence: self-consistency, evidence grounding, and whether a claimed contradiction is actually supported.

**05:24**  Then the deterministic Controller decides. Nine trusted, no contradiction, risk low: AUTO_OPTIMIZE at a hundred percent confidence.

**05:32**  Single-digit milliseconds for the whole chain — gate, correlation, verifier and controller are pure code.

---

## Chapter 5 — Vehicle Explorer

*05:38 · Telemetry, world state, trust, freshness, confidence · 0.80 min*

**05:40**  The Vehicle Explorer is the per-asset view.

**05:44**  Four headline numbers: was the gate clean, what share of evidence was fresh, the computed confidence, and the policy pack in force.

**05:52**  Confidence history across the session. Below it, live telemetry — raw world state, ground truth, before anything is gated or graded.

**06:00**  The gate does its work between that and what comes next.

**06:04**  These panels are what each agent reported after the gate graded it. Keeping raw truth and gated evidence separate is the point.

**06:14**  Each reading shows freshness and source. Exclusions are shown as exclusions, not silently dropped.

**06:19**  And the risk assessment: level, contradiction flag, cited factors, reasoning summary. Presented as an opinion, which is all it is.

---

## Chapter 6 — The Pipeline Page

*06:28 · The five layers against one real run · 0.36 min*

**06:30**  The Pipeline page pins the same run against the architecture.

**06:36**  Telemetry agents, Trust Gate, Risk Assessment Engine, deterministic Controller, Action Gateway.

**06:40**  Underneath: sensors reporting, evidence trusted versus ignored, the AI review, the decision, whether anything went for approval — then every gate exclusion written out in plain language.

---

## Chapter 7 — Runtime Deep Dive

*06:51 · Supervisor, metrics, confidence, memory, certificate · 2.14 min*

**06:53**  Back to the Runtime, reading live state rather than the diagram.

**06:58**  The Supervisor Console logs what the Supervisor actually did: planned, launched each agent by name, collected signals, completed.

**07:06**  Underneath: agents launched, agent failures, retries, and whether a retry recovered.

**07:10**  Harness Metrics are aggregated server-side over everything persisted, not counters held in memory: runs, success rate, halts, retries, evidence rejected, breaker trips, actions, confidence, latency.

**07:21**  Confidence Computation shows the arithmetic, not just the number.

**07:24**  Corroborating signals over expected signals — nine under the cold chain pack — minus a flat two-signal penalty for a detected contradiction.

**07:33**  Computed in code. The model is forbidden from reporting a confidence field: that key is not in the schema, and output carrying it is rejected.

**07:42**  Below it, the composite trust score: five independently observable factors, multiplied.

**07:46**  Evidence quality is that same tested formula; verifier score is one if the verifier passed, one half if not; gate cleanliness is trusted over total evidence; policy compliance loses a quarter per physical conflict; historical reliability is the vehicle's recent non-halt rate.

**08:01**  None of the five is self-reported by the model. Each is measured somewhere else in the system.

**08:07**  One thing the diagram does not draw: the Event Bus. Every stage publishes a typed event rather than calling Audit directly — Audit is just one subscriber, the vocabulary is fixed at sixteen event types, and a metrics collector or websocket pusher could subscribe without the Supervisor knowing.

**08:24**  Signal Trend is Memory: one signal across the vehicle's past runs, read back out of the store, with a direction and a delta.

**08:34**  World State again, labelled pre-gate so it is never mistaken for evidence. The Decision Certificate then closes the run with five checks, each derived from a real field on the decision.

**08:46**  Five checks, five stored facts.

**08:49**  Incident Memory is a different subsystem from Memory. Memory asks whether a signal is drifting; Incident Memory asks what went wrong and whether it was resolved. Empty now — we will come back once we break something.

---

## Chapter 8 — Contradictory Evidence

*09:03 · The failure the architecture exists for · 1.68 min*

**09:05**  Now the failure scenario, where the architecture earns its keep.

**09:09**  Cooling reports ON. Cargo is eleven point five degrees, nearly double the safe band. Ambient forty-one. Stopped for thirty-seven minutes.

**09:17**  Those two facts cannot both be true. Either the cooling unit is not really running, or the cargo sensor is wrong. Something is lying.

**09:26**  Run it.

**09:35**  Correlation caught it deterministically, before the model reasoned at all: cooling on, cargo above the safe maximum. It also flagged thermal dwell risk.

**09:44**  The Risk Assessment Engine reasoned over the same evidence and reached HIGH risk with the contradiction flag set, citing four factors.

**09:52**  The Verifier checked it against the evidence: high risk backed by factors, every factor mapped to a present signal, and enough evidence behind the contradiction. All three passed.

**10:02**  Confidence fell from a hundred percent to seventy-eight: nine trusted, minus the two-signal contradiction penalty, over nine expected.

**10:08**  Notice what did not happen. The model did not decide — it produced an assessment.

**10:14**  The Controller is a state machine: three states, first match wins, in the order agents down, output rejected, evidence missing, confirmed risk, healthy.

**10:23**  It reached rule four — risk high or contradiction flagged. CRITICAL_HALT. And it is the only component permitted to request an action.

**10:31**  The decision explainer puts the whole chain in one place: final state, the reasoner's output, the verifier's status, the confidence arithmetic, and the evidence it was grounded in.

**10:43**  Every claim there is a field on the stored decision. Nothing is re-derived in the browser.

---

## Chapter 9 — Human Approval

*10:51 · The Action Gateway and the escalation record · 0.89 min*

**10:53**  The Action Gateway is the authority boundary — the only place an action can be requested, approved and executed.

**11:01**  Halting automation is human-tier. It does not execute. It opens for approval and waits.

**11:07**  Nothing inside the system can move it forward. Only a person can.

**11:11**  Approve it.

**11:15**  The gateway moves it to approved, then executes — which here means creating an immutable escalation record. Three rows land on the action's own event log: requested, approved, executed, each with an actor and a timestamp.

**11:29**  An operator can also reject with a reason, recorded just as durably. A decision not to act is still a decision.

**11:36**  Every transition also lands in the append-only audit table under a fixed event vocabulary, which is what makes the trail queryable end to end.

---

## Chapter 10 — The Failure Matrix

*11:46 · Every failure mode the harness claims to survive · 2.41 min*

**11:48**  The Simulation Lab drives every failure mode the harness claims to survive. Each control hits a real endpoint. Back to normal conditions first, so each failure is isolated.

**11:59**  Failure one: an agent dies mid-route.

**12:02**  The Environment Agent is unavailable. The harness does not guess the missing values and does not proceed on half a picture.

**12:12**  Rule one fires: agents unavailable. INSUFFICIENT_DATA at fifty-six percent, five of nine signals surviving. It did not crash — it degraded and stayed up.

**12:20**  Failure two: the model returns malformed output.

**12:23**  The payload is valid JSON but violates the contract: no reasoning summary, plus a confidence field the model is forbidden to set. It goes through the same strict validation a real model's output would. Two validation errors — rejected, not coerced into shape.

**12:41**  Rule two fires: critic output rejected, INSUFFICIENT_DATA.

**12:44**  And confidence is still a hundred percent. Not a bug: confidence measures evidence completeness, and the evidence was complete. The model failing is a separate axis, refused independently.

**12:54**  Failure three: stale telemetry. One cargo reading backdated four minutes.

**12:58**  The gate recomputes age from the timestamp, so it lands past the freshness window and is excluded.

**13:08**  Cargo temperature is required, so rule three fires: required evidence missing or untrusted. Eighty-nine percent, INSUFFICIENT_DATA.

**13:14**  Failure four: a network blip on the one call that crosses a real network boundary. The next risk-assessment call fails once.

**13:22**  The Retry Engine tries again inside the same run, and recovers.

**13:31**  There is the retry row, marked attempt failed, and the recovered marker on the stage that succeeded second time.

**13:40**  System Indicators tracks all of it live, including open escalations.

**13:44**  Failure five: three consecutive model failures open the Circuit Breaker.

**13:48**  Now it stops attempting the call at all rather than sitting on timeouts, and records that the breaker was open on that run.

**13:59**  After the cooldown it half-opens, and the next successful call closes it. No restart needed.

**14:17**  Two more injections. Sensor drift pushes cargo to fourteen and a half.

**14:21**  And the red override forces the worst case: fifteen degrees, with cooling still insisting it is running.

---

## Chapter 11 — Policy Packs

*14:30 · The domain is data, not code · 1.19 min*

**14:32**  Everything so far was cold chain. But nothing in the gate, correlation, verifier or controller knows what cold chain is.

**14:40**  The domain lives in a policy pack. Two ship today.

**14:44**  Cold Chain requires cargo temperature, cooling status and ambient temperature, and expects nine signals. Tyre Safety requires tyre pressure, tyre temperature and vehicle speed, and expects five.

**14:54**  Switch the active pack to Tyre Safety and run the very same world again.

**15:09**  Same world, same code paths, completely different outcome.

**15:12**  Cargo temperature, cooling status, weather severity and dwell are now excluded as unknown signals — they are not in this policy's vocabulary at all.

**15:21**  The expected denominator moved from nine to five, so the confidence arithmetic changed underneath it.

**15:26**  And the reasoner switched to tyre logic: the contradiction it hunts is underinflation plus heat, not cooling versus cargo.

**15:33**  Telemetry that halted automation under Cold Chain runs clean under Tyre Safety, because policy decides what counts as evidence and what counts as risk. Not the model.

**15:45**  Zero code changes in gate, correlation, risk engine or controller. Switch back.

---

## Chapter 12 — Isolation

*15:50 · Why the AI cannot act, by construction · 1.08 min*

**15:52**  Now the guarantee most systems assert and few demonstrate: the AI components cannot act.

**15:57**  That button makes the Vehicle Agent genuinely attempt to call the Environment Agent's tool.

**16:04**  Denied by the Tool Registry — scoped access, checked at call time.

**16:09**  The red-team probe goes further. It inspects the live agent object for seven action-shaped attributes, then parses the agents module's import graph to see whether it can even reach the action gateway.

**16:23**  Eight attempts, all blocked — not by a permission check that could be misconfigured, but by the absence of any reference at all.

**16:31**  The agents module does not import actions; neither does the critic. There is no object to call. And it is enforced by tests, not convention — the isolation suite fails the build the moment anyone wires an action onto an agent.

**16:46**  Ninety-eight tests cover the gate, policy, critic validation, confidence, the controller table, the gateway, the HTTP surface and the runtime — plus property-based fuzzing over random inputs.

---

## Chapter 13 — Replay and Audit

*16:56 · Reconstructing a decision after the fact · 1.04 min*

**16:58**  Replay. Every run is durably persisted: the decision, its evidence snapshot, the gate notes, the verifier result, the timed trace. The audit trail is append-only — nothing in it is ever rewritten.

**17:11**  Filterable by event type.

**17:14**  And searchable across the whole trail.

**17:18**  Selecting any record with a run reconstructs that decision out of storage: its stepper, its state, its reason, and the reasoning summary current at the time.

**17:30**  And the trace replays stage by stage, paced by the durations actually recorded.

**17:39**  Incident Memory has filled in: the halts we caused, joined with how each action was resolved, and by whom.

**17:48**  That is what makes an incident reviewable by someone who was not in the room: not a log line, but the exact evidence, the exact assessment, the exact rule that fired, and who approved what.

---

## Chapter 14 — Analytics and Configuration

*18:01 · Every chart, and the harness settings · 0.71 min*

**18:03**  Analytics aggregates the session.

**18:06**  Runs, schema rejections, contradictions flagged, security probe pass rate.

**18:10**  The Decision Funnel is the most useful view: how many runs reached each gate — runs, evidence complete, risk assessed, verifier passed, automation continued.

**18:20**  The drop-off between stages is where the harness refused to proceed. Every step down is a decision not taken.

**18:27**  Confidence over time, and the distribution across the three controller states.

**18:31**  Then four health gauges: confidence, healthy decisions, reasoner validity, security integrity.

**18:37**  Settings carries view mode and environment: which reasoning backend is live, the active scenario, and the API base being polled.

---

## Chapter 15 — Confidence and Authority

*18:46 · The two ideas the design rests on · 1.07 min*

**18:48**  Two ideas hold this design together.

**18:51**  First, confidence: a measure of evidence, computed in code, with a fixed denominator that data loss cannot cancel out.

**18:58**  If the denominator were whatever you happened to receive, losing an agent would leave you at a hundred percent confidence in a smaller picture. It is not. It is what a healthy fleet produces.

**19:10**  So a killed agent, an excluded stale reading, or a contradiction genuinely lowers the number. That is the only safe behaviour.

**19:17**  Second, authority. The model's output is an input to a decision, never the decision.

**19:23**  Validated against a strict schema, verified against its evidence, then consumed by a state machine you can read in about forty lines.

**19:31**  The Controller is the only component permitted to request an action, in one of its three states — and halting automation is human-tier, so it opens for approval and waits.

**19:42**  Which means if the model is unavailable, malformed, contradictory or simply wrong, the worst outcome this system can reach is a refusal to act.

---

## Chapter 16 — Closing

*19:51 · Agents investigate. The Critic challenges. Policy decides. · 0.89 min*

**19:53**  Five layers, five modules, never collapsed into one.

**19:57**  Intelligence: two isolated agents and one reasoner with no tools and no authority.

**20:02**  Evidence: a deterministic trust gate — freshness, provenance, completeness, normalization. Policy: swappable domain packs that decide what counts as evidence and what counts as risk.

**20:11**  Decision: a three-state machine and a confidence formula, both in code. Authority: one gateway, human-tier approval, an append-only record of every transition.

**20:19**  The app even ships its own presenter guide, mapping each scene to the module that guarantees it.

**20:29**  Intelligence is advisory. Deterministic policy is authoritative. Every screen here is an argument for that.

**20:36**  Agents investigate.

**20:38**  The Critic challenges.

**20:41**  Deterministic policy decides.

---

## The last three lines

> **Agents investigate.**
>
> **The Critic challenges.**
>
> **Deterministic policy decides.**

Deliver them slowly, with a full beat between each. Do not add a summary afterwards.
