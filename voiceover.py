import asyncio
import edge_tts

async def generate_voiceover():
    # Paste your full subtitle text here (from Claude)
    text = """
    Fleet-Harness is not an AI agent. It is a trust harness: a decision-control layer between AI reasoning and a real operational action.


The asset is a refrigerated truck, TRUCK-042, carrying cargo that spoils outside a two-to-six degree band.


The obvious design hands the telemetry to a language model and lets it decide. That design fails in three ways.


It trusts whatever data arrives: stale, duplicated, or from the wrong sensor.


It trusts whatever the model says: malformed, ungrounded, or internally contradictory.


And it gives the model authority to change something physical.


Fleet-Harness splits those three concerns into separate modules that never collapse back into one call. Intelligence is advisory, evidence is gated, deterministic policy is authoritative — each boundary enforced in code and backed by a test.


It boots with no API key: a deterministic mock reasoner stands in, so nothing here depends on the network.


This is the Harness Runtime. Every box maps to a real backend module.


The Supervisor starts each agent, times every stage, retries the one call that crosses a network boundary, and assembles the execution trace.


The State Manager is RunState: one object per run that every stage reads and writes, instead of variables threaded from function to function.


The Scheduler is the Planner. It decides which agents run, and whether they may run in parallel.


The Retry Engine bounds retries inside one run. The Circuit Breaker is separate: it decides whether to attempt the call at all, across runs.


The Policy Engine selects the active domain pack. The gate, the correlation engine and the reasoner all read from whichever pack is active.


The Execution Trace times every stage, including retries and the four Trust Gate sub-stages.


Memory tracks a signal across a vehicle's past runs, so the harness judges a trend, not a snapshot.


Audit is an append-only log of every meaningful transition.


The line underneath is the real call order: Planner, Supervisor running agents, gate, correlation, risk assessment, verifier, controller — then the Harness, which persists and decides whether to request an action.


The same architecture as five layers, each in its own module: Intelligence, Evidence, Policy, Decision, Authority — never collapsed into one model call. That separation is the product.


The operator's view is a control room, not a KPI wall.


Top line: decisions waiting on a human, vehicles monitored, harness runs this session. The Harness Trust Score beside it composites four measured things — evidence freshness, agent health, schema validity, verifier checks.


Beside it the counterfactual: what an unconstrained model with direct fleet-API access would do with this telemetry. That figure is an illustrative loss, not a measurement.


The five-layer strip is live — each box takes its colour from the run that just executed. Under it, the failure injection bar: every button calls a real endpoint, none is staged.


Live Execution animates the real call order: two agents in parallel, gate, risk assessment, decision authority, action gateway.


Beside it the events feed — the same audit stream the Audit page reads.


Then the decision trace, every stage's duration in milliseconds.


Then provenance: every reading carries a sensor id, a hash of its raw payload, and the transformations applied to it.


At the bottom, the controller banner and the approvals queue — the only place an action is ever released. The speed selector up top changes how often the dashboard polls.


And Simple versus Technical: plain English for an operator, or the internal vocabulary underneath it.


A healthy run, end to end.


Both agents light first, together, then the gate, risk assessment, the decision, the gateway.


The Planner dispatched both observers in parallel because their scopes are provably disjoint: the Vehicle Agent sees only the truck's sensors, the Environment Agent only route and weather.


Nine signals collected — five from the truck, four from the environment.


The Trust Gate ran four sub-stages over them, broken out inside the gate step.


Schema Validator: every reading is a well-formed, typed observation. Freshness Checker: age recomputed from the timestamp, never trusted from a status field — under two minutes fresh, past five minutes invalid.


Provenance Checker: each signal has exactly one authorized source agent. A reading from the wrong agent is excluded even when the value looks fine.


Evidence Normalizer: one trusted reading per signal, the freshest. That is what makes the confidence denominator a real upper bound.


Then Correlation runs deterministic physical checks before the model reasons at all: cooling on while cargo is warm, heat plus long dwell, cargo too cold for the ambient with cooling off.


Only then does the Risk Assessment Engine reason, over structured evidence only. No tools, no world state, no action function.


The Verifier checks the model against its evidence: self-consistency, evidence grounding, and whether a claimed contradiction is actually supported.


Then the deterministic Controller decides. Nine trusted, no contradiction, risk low: AUTO_OPTIMIZE at a hundred percent confidence.


Single-digit milliseconds for the whole chain — gate, correlation, verifier and controller are pure code.


The Vehicle Explorer is the per-asset view.


Four headline numbers: was the gate clean, what share of evidence was fresh, the computed confidence, and the policy pack in force.


Confidence history across the session. Below it, live telemetry — raw world state, ground truth, before anything is gated or graded.


The gate does its work between that and what comes next.


These panels are what each agent reported after the gate graded it. Keeping raw truth and gated evidence separate is the point.


Each reading shows freshness and source. Exclusions are shown as exclusions, not silently dropped.


And the risk assessment: level, contradiction flag, cited factors, reasoning summary. Presented as an opinion, which is all it is.


The Pipeline page pins the same run against the architecture.


Telemetry agents, Trust Gate, Risk Assessment Engine, deterministic Controller, Action Gateway.


Underneath: sensors reporting, evidence trusted versus ignored, the AI review, the decision, whether anything went for approval — then every gate exclusion written out in plain language.


Back to the Runtime, reading live state rather than the diagram.


The Supervisor Console logs what the Supervisor actually did: planned, launched each agent by name, collected signals, completed.


Underneath: agents launched, agent failures, retries, and whether a retry recovered.


Harness Metrics are aggregated server-side over everything persisted, not counters held in memory: runs, success rate, halts, retries, evidence rejected, breaker trips, actions, confidence, latency.


Confidence Computation shows the arithmetic, not just the number.


Corroborating signals over expected signals — nine under the cold chain pack — minus a flat two-signal penalty for a detected contradiction.


Computed in code. The model is forbidden from reporting a confidence field: that key is not in the schema, and output carrying it is rejected.


Below it, the composite trust score: five independently observable factors, multiplied.


Evidence quality is that same tested formula; verifier score is one if the verifier passed, one half if not; gate cleanliness is trusted over total evidence; policy compliance loses a quarter per physical conflict; historical reliability is the vehicle's recent non-halt rate.


None of the five is self-reported by the model. Each is measured somewhere else in the system.


One thing the diagram does not draw: the Event Bus. Every stage publishes a typed event rather than calling Audit directly — Audit is just one subscriber, the vocabulary is fixed at sixteen event types, and a metrics collector or websocket pusher could subscribe without the Supervisor knowing.


Signal Trend is Memory: one signal across the vehicle's past runs, read back out of the store, with a direction and a delta.


World State again, labelled pre-gate so it is never mistaken for evidence. The Decision Certificate then closes the run with five checks, each derived from a real field on the decision.


Five checks, five stored facts.


Incident Memory is a different subsystem from Memory. Memory asks whether a signal is drifting; Incident Memory asks what went wrong and whether it was resolved. Empty now — we will come back once we break something.


Now the failure scenario, where the architecture earns its keep.


Cooling reports ON. Cargo is eleven point five degrees, nearly double the safe band. Ambient forty-one. Stopped for thirty-seven minutes.


Those two facts cannot both be true. Either the cooling unit is not really running, or the cargo sensor is wrong. Something is lying.


Run it.


Correlation caught it deterministically, before the model reasoned at all: cooling on, cargo above the safe maximum. It also flagged thermal dwell risk.


The Risk Assessment Engine reasoned over the same evidence and reached HIGH risk with the contradiction flag set, citing four factors.


The Verifier checked it against the evidence: high risk backed by factors, every factor mapped to a present signal, and enough evidence behind the contradiction. All three passed.


Confidence fell from a hundred percent to seventy-eight: nine trusted, minus the two-signal contradiction penalty, over nine expected.


Notice what did not happen. The model did not decide — it produced an assessment.


The Controller is a state machine: three states, first match wins, in the order agents down, output rejected, evidence missing, confirmed risk, healthy.


It reached rule four — risk high or contradiction flagged. CRITICAL_HALT. And it is the only component permitted to request an action.


The decision explainer puts the whole chain in one place: final state, the reasoner's output, the verifier's status, the confidence arithmetic, and the evidence it was grounded in.


Every claim there is a field on the stored decision. Nothing is re-derived in the browser.


The Action Gateway is the authority boundary — the only place an action can be requested, approved and executed.


Halting automation is human-tier. It does not execute. It opens for approval and waits.


Nothing inside the system can move it forward. Only a person can.


Approve it.


The gateway moves it to approved, then executes — which here means creating an immutable escalation record. Three rows land on the action's own event log: requested, approved, executed, each with an actor and a timestamp.


An operator can also reject with a reason, recorded just as durably. A decision not to act is still a decision.


Every transition also lands in the append-only audit table under a fixed event vocabulary, which is what makes the trail queryable end to end.


The Simulation Lab drives every failure mode the harness claims to survive. Each control hits a real endpoint. Back to normal conditions first, so each failure is isolated.


Failure one: an agent dies mid-route.


The Environment Agent is unavailable. The harness does not guess the missing values and does not proceed on half a picture.


Rule one fires: agents unavailable. INSUFFICIENT_DATA at fifty-six percent, five of nine signals surviving. It did not crash — it degraded and stayed up.


Failure two: the model returns malformed output.


The payload is valid JSON but violates the contract: no reasoning summary, plus a confidence field the model is forbidden to set. It goes through the same strict validation a real model's output would. Two validation errors — rejected, not coerced into shape.


Rule two fires: critic output rejected, INSUFFICIENT_DATA.


And confidence is still a hundred percent. Not a bug: confidence measures evidence completeness, and the evidence was complete. The model failing is a separate axis, refused independently.


Failure three: stale telemetry. One cargo reading backdated four minutes.


The gate recomputes age from the timestamp, so it lands past the freshness window and is excluded.


Cargo temperature is required, so rule three fires: required evidence missing or untrusted. Eighty-nine percent, INSUFFICIENT_DATA.


Failure four: a network blip on the one call that crosses a real network boundary. The next risk-assessment call fails once.


The Retry Engine tries again inside the same run, and recovers.


There is the retry row, marked attempt failed, and the recovered marker on the stage that succeeded second time.


System Indicators tracks all of it live, including open escalations.


Failure five: three consecutive model failures open the Circuit Breaker.


Now it stops attempting the call at all rather than sitting on timeouts, and records that the breaker was open on that run.


After the cooldown it half-opens, and the next successful call closes it. No restart needed.


Two more injections. Sensor drift pushes cargo to fourteen and a half.


And the red override forces the worst case: fifteen degrees, with cooling still insisting it is running.


Everything so far was cold chain. But nothing in the gate, correlation, verifier or controller knows what cold chain is.


The domain lives in a policy pack. Two ship today.


Cold Chain requires cargo temperature, cooling status and ambient temperature, and expects nine signals. Tyre Safety requires tyre pressure, tyre temperature and vehicle speed, and expects five.


Switch the active pack to Tyre Safety and run the very same world again.


Same world, same code paths, completely different outcome.


Cargo temperature, cooling status, weather severity and dwell are now excluded as unknown signals — they are not in this policy's vocabulary at all.


The expected denominator moved from nine to five, so the confidence arithmetic changed underneath it.


And the reasoner switched to tyre logic: the contradiction it hunts is underinflation plus heat, not cooling versus cargo.


Telemetry that halted automation under Cold Chain runs clean under Tyre Safety, because policy decides what counts as evidence and what counts as risk. Not the model.


Zero code changes in gate, correlation, risk engine or controller. Switch back.


Now the guarantee most systems assert and few demonstrate: the AI components cannot act.


That button makes the Vehicle Agent genuinely attempt to call the Environment Agent's tool.


Denied by the Tool Registry — scoped access, checked at call time.


The red-team probe goes further. It inspects the live agent object for seven action-shaped attributes, then parses the agents module's import graph to see whether it can even reach the action gateway.


Eight attempts, all blocked — not by a permission check that could be misconfigured, but by the absence of any reference at all.


The agents module does not import actions; neither does the critic. There is no object to call. And it is enforced by tests, not convention — the isolation suite fails the build the moment anyone wires an action onto an agent.


Ninety-eight tests cover the gate, policy, critic validation, confidence, the controller table, the gateway, the HTTP surface and the runtime — plus property-based fuzzing over random inputs.


Replay. Every run is durably persisted: the decision, its evidence snapshot, the gate notes, the verifier result, the timed trace. The audit trail is append-only — nothing in it is ever rewritten.


Filterable by event type.


And searchable across the whole trail.


Selecting any record with a run reconstructs that decision out of storage: its stepper, its state, its reason, and the reasoning summary current at the time.


And the trace replays stage by stage, paced by the durations actually recorded.


Incident Memory has filled in: the halts we caused, joined with how each action was resolved, and by whom.


That is what makes an incident reviewable by someone who was not in the room: not a log line, but the exact evidence, the exact assessment, the exact rule that fired, and who approved what.


Analytics aggregates the session.


Runs, schema rejections, contradictions flagged, security probe pass rate.


The Decision Funnel is the most useful view: how many runs reached each gate — runs, evidence complete, risk assessed, verifier passed, automation continued.


The drop-off between stages is where the harness refused to proceed. Every step down is a decision not taken.


Confidence over time, and the distribution across the three controller states.


Then four health gauges: confidence, healthy decisions, reasoner validity, security integrity.


Settings carries view mode and environment: which reasoning backend is live, the active scenario, and the API base being polled.


Two ideas hold this design together.


First, confidence: a measure of evidence, computed in code, with a fixed denominator that data loss cannot cancel out.


If the denominator were whatever you happened to receive, losing an agent would leave you at a hundred percent confidence in a smaller picture. It is not. It is what a healthy fleet produces.


So a killed agent, an excluded stale reading, or a contradiction genuinely lowers the number. That is the only safe behaviour.


Second, authority. The model's output is an input to a decision, never the decision.


Validated against a strict schema, verified against its evidence, then consumed by a state machine you can read in about forty lines.


The Controller is the only component permitted to request an action, in one of its three states — and halting automation is human-tier, so it opens for approval and waits.


Which means if the model is unavailable, malformed, contradictory or simply wrong, the worst outcome this system can reach is a refusal to act.


Five layers, five modules, never collapsed into one.


Intelligence: two isolated agents and one reasoner with no tools and no authority.


Evidence: a deterministic trust gate — freshness, provenance, completeness, normalization. Policy: swappable domain packs that decide what counts as evidence and what counts as risk.


Decision: a three-state machine and a confidence formula, both in code. Authority: one gateway, human-tier approval, an append-only record of every transition.


The app even ships its own presenter guide, mapping each scene to the module that guarantees it.


Intelligence is advisory. Deterministic policy is authoritative. Every screen here is an argument for that.


Agents investigate.


The Critic challenges.


Deterministic policy decides.
    """
    
    voice = "en-US-JennyNeural"  # Natural female voice
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save("voiceover.mp3")
    print("✅ voiceover.mp3 generated!")

asyncio.run(generate_voiceover())

