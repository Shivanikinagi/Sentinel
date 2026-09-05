# Presenter Notes — Fleet-Harness Master Demo

Speaking notes for driving the master walkthrough live, or for narrating over the
recorded run. Pairs with `narration.md` (the words) and `master_demo.md` (the
structure).

**Total: 20 min 46 s as recorded, 16 chapters.** Chapter headings below carry the start time in the recorded run and the narration length. Live delivery runs longer — you will pause for questions.

---

## Pre-flight (5 minutes before)

```bash
cd backend && python -m pytest -q          # expect: 98 passed
cd ../frontend && npm run dev              # :5173
cd ../backend && python -m uvicorn app.main:app --port 8000
curl -s -X POST http://localhost:8000/simulate/reset
```

Checklist:

- [ ] `GET /health` returns `critic_backend: "mock"` (or `openrouter` if you are
      showing the real model — say which, on camera).
- [ ] Store reset, then 2–3 healthy runs seeded so trends and metrics are not
      empty. `create_master_demo.py` does this automatically; do it by hand if driving live.
- [ ] Active policy pack is `cold_chain`. If a previous rehearsal left it on
      `tyre_safety`, Chapter 4's numbers will be wrong.
- [ ] Circuit breaker closed. If you tripped it in rehearsal, wait 30 s and do one
      run before you start.
- [ ] Browser at 1920×1080, view mode on **Simple**.
- [ ] Zoom the browser to 100 %. The 5-layer strip wraps below ~1500 px.

**Fastest full reset:** `python demo/create_master_demo.py --dry-run` prints the plan;
`python demo/create_master_demo.py --speed 8 --no-video` re-runs the whole thing in about
six minutes and leaves the system in a demo-ready state.

---

## The one thing to land

Every chapter is in service of a single sentence:

> **Intelligence is advisory. Deterministic policy is authoritative.**

If you have to cut on the fly, cut *pages*, never *arguments*. A technical
audience will forgive not seeing the Analytics tab. They will not forgive not
understanding why the model cannot act.

---

## Chapter notes

### Ch 1 — The Problem — 00:05 (0:57)

**Cue:** Dashboard at rest.

Open on the distinction, not the product: *"this is not an AI agent, it is a trust
harness."* Say it in the first ten seconds — it reframes everything after it.

The three failure modes of the naive design are the spine of the whole demo. Count
them on your fingers: **bad data, bad reasoning, unearned authority.** You will
come back to each one (Ch 10, Ch 8, Ch 12).

Point at the **LLM Zero Decision Authority** badge in the topbar. Then at the
model badge and say the no-API-key line — get the "is this real?" objection out of
the way early rather than letting it sit in someone's head for twenty minutes.

> ⚠️ Say the mock-reasoner line *proactively*. If an audience discovers it at
> minute 15 it reads as a reveal; said at minute 1 it reads as rigour.

### Ch 2 — Architecture — 01:03 (1:26)

**Cue:** `/runtime`, the 8-tile diagram.

Go tile by tile. The two lines that matter most:

- **RunState** — "one object per run that every stage reads and writes, instead of
  variables threaded from function to function." That is the sentence that makes
  this a runtime and not a pipeline function.
- **Retry Engine vs. Circuit Breaker** — retry is *within* a run, the breaker is
  *across* runs. Engineers notice when you conflate these; they notice more when
  you don't.

End on the flow-order line under the diagram, then jump to `/pipeline` for the
five layers. Don't linger — Chapter 6 comes back to this page.

### Ch 3 — The Dashboard — 02:31 (1:21)

**Cue:** `/`, scrolling top to bottom.

This is the widest chapter and the easiest to run long. Keep it moving; nothing
here needs defending, you are just naming things.

Two honesty beats you must not skip:

- The counterfactual card's dollar figure is **illustrative**. Say "illustrative
  loss, not a measurement."
- The speed selector changes the **dashboard's poll interval**, nothing about the
  harness.

The Simple/Technical toggle is worth ten seconds: it is the same data with the
internal vocabulary switched on. Flip to Technical, let them see the captions
appear, flip back.

### Ch 4 — A Healthy Run — 03:54 (1:39)

**Cue:** Healthy scene → Run check. **Let the animation finish before you talk
over the result.**

This is the chapter where you earn the right to be believed later. Narrate the
*order*, and be precise about the parallel claim: the Planner runs both observers
concurrently **because their scopes are provably disjoint** — that is a test
(`test_vehicle_observer_cannot_reach_environment_scope`), not an assumption.

Scroll to the trust gate step and let the four sub-stage chips sit on screen while
you name them. The Evidence Normalizer line is the subtle one — *"at most one
trusted reading per signal, the freshest, which is what makes the confidence
denominator a real upper bound."* That is a real bug that property-based fuzzing
caught; if anyone asks, tell them.

Land on `AUTO_OPTIMIZE` / **100 %** / single-digit milliseconds.

### Ch 5 — Vehicle Explorer — 05:38 (0:48)

**Cue:** `/vehicle`.

One idea: **raw world state and gated evidence are shown as two different things.**
That separation is the page's whole argument. If you say nothing else here, say
"the gate is what happens between these two panels."

### Ch 6 — The Pipeline Page — 06:28 (0:22)

Shortest chapter. It exists so the audience sees the architecture *pinned to one
concrete run*. Do not re-explain the layers — you did that in Ch 2.

### Ch 7 — Runtime Deep Dive — 06:51 (2:08)

**Cue:** `/runtime`, live state this time.

Longest chapter after the failure matrix. Structure it as three groups so it does
not feel like a list:

1. **What ran** — Supervisor Console + counters.
2. **What is measured** — Metrics, Event Bus, Confidence, Composite.
3. **What is remembered** — Signal Trend (Memory), Decision Certificate, Incident
   Memory.

The **Event Bus** has no tile on the diagram, so it is easy to skip. Don't:
"every stage publishes a typed event rather than calling Audit directly; Audit is
one subscriber." That is the line that explains why adding a websocket pusher or a
metrics collector needs no change to the Supervisor.

On the composite score, the phrase that lands is: **"none of the five is
self-reported by the model."**

Incident Memory is **empty here on purpose**. Say so — "we'll come back once we
break something." It pays off in Chapter 13.

### Ch 8 — Contradictory Evidence — 09:03 (1:41)

**Cue:** Risk Anomaly → Run check. The centrepiece. Slow down.

Set up the physical impossibility *before* you run it: cooling reports ON, cargo
is 11.5 °C, ambient 41 °C, stopped 37 minutes. **"Those two facts cannot both be
true."** Pause there.

Then walk the four independent things that happen, in order, and make clear they
are independent:

1. Correlation catches it **deterministically, before the model reasons at all.**
2. The model reasons and reaches HIGH + contradiction.
3. The Verifier checks the model **against its own evidence** — three checks.
4. The Controller decides.

The line to land: **"Notice what did not happen. The model did not decide. It
produced an assessment."**

Confidence 100 % → 78 %, and say the arithmetic out loud: nine trusted, minus the
two-signal contradiction penalty, over nine expected.

Then the Controller's rule ordering. Five rules, first match wins; this hits rule
four. Emphasise: **the Controller is the only component permitted to request an
action.**

Close on the Decision Explainer and the line *"every claim there is a field on the
stored decision."*

### Ch 9 — Human Approval — 10:51 (0:53)

**Cue:** the pending action card.

"Halting automation is **human-tier**. It does not execute. It opens for approval
and waits." Then: **"nothing inside the system can move it forward. Only a
person can."**

Click Approve. Point at the three event rows — requested, approved, executed —
each with an actor and a timestamp. Mention that rejection with a reason is
recorded just as durably: *a decision not to act is still a decision.*

### Ch 10 — The Failure Matrix — 11:46 (2:25)

**Cue:** `/simulation`. Click **Normal conditions** first — otherwise the killed
agent run inherits the contradiction penalty and reads 33 %, not 56 %.

Seven injections, brisk. Do not editorialise on every one; the volume is the
argument. But **stop dead on failure two.**

> **The corrupt-model beat is the smartest moment in the demo.** Confidence stays
> at **100 %** while the state drops to `INSUFFICIENT_DATA`. That looks like a bug
> for about two seconds, and then it is the whole thesis:
> *confidence measures evidence completeness, and the evidence was complete. The
> model failing is a separate axis, and the Controller refuses on that axis
> independently.* Two orthogonal guards, not one blended score.

If someone is going to interrupt with a question, it will be here. Let them.

The breaker has a **30-second cooldown**. If you are driving live, do the sensor
drift and override beats while it recovers, then run once before Chapter 11 —
otherwise the policy-pack run will come back "Circuit Breaker is OPEN" and you
will demo the wrong thing. (`create_master_demo.py` handles this automatically via
`ensure_breaker_closed()`.)

### Ch 11 — Policy Packs — 14:30 (1:11)

**Cue:** `/runtime`, Policy Engine card.

Open with the strong claim: **"nothing in the gate, correlation engine, verifier
or controller knows what cold chain is."**

Switch to Tyre Safety, run the **same world state**, and let the result speak: the
telemetry that halted automation now runs clean. Then explain why — the cold-chain
signals are excluded as *unknown signals*, not as bad ones; they are not in this
policy's vocabulary at all. Denominator 9 → 5. Reasoner switches to
underinflation-plus-heat.

Punchline: **"policy decides what counts as evidence and what counts as risk. Not
the model."** Then: zero code changes in gate, correlation, risk engine or
controller.

**Switch back to Cold Chain before moving on.** Easy to forget; it breaks
everything after it.

### Ch 12 — Isolation — 15:50 (1:05)

**Cue:** Isolation Proof card.

Both probes are **live and unstaged** — say that, because it is the claim people
assume is theatre.

The distinction that matters: *"not by a permission check that could be
misconfigured, but by the absence of any reference at all."* `agents.py` does not
import `actions.py`. There is no object to call.

Then the test point: `tests/test_isolation.py` fails the build the moment anyone
wires an action onto an agent. 98 tests total, plus property-based fuzzing.

If you have a terminal handy, running `pytest -q` live here is worth 20 seconds.

### Ch 13 — Replay and Audit — 16:56 (1:02)

**Cue:** `/audit`.

Filter, search, select a record. The payoff line is the last one, and it is aimed
at anyone who has ever done an incident review:

> **"Not a log line saying the system halted, but the exact evidence, the exact
> assessment, the exact rule that fired, and who approved what."**

Then the Replay Incident button on the trace, and Incident Memory — now populated,
as promised in Chapter 7.

### Ch 14 — Analytics and Configuration — 18:01 (0:43)

Fast. The **Decision Funnel** is the only chart worth dwelling on: *"the drop-off
between stages is where the harness refused to proceed. Every step down is a
decision not taken."*

### Ch 15 — Confidence and Authority — 18:46 (1:04)

**Cue:** `/runtime`, confidence arithmetic on screen.

This is the intellectual close. Two ideas, precisely.

**Confidence — the fixed denominator.** The counterfactual makes it land: *"if the
denominator were whatever you happened to receive, losing an agent would leave you
at a hundred percent confidence in a smaller picture."* Then: the model is
**forbidden** from reporting confidence — `extra="forbid"`, output carrying it is
rejected.

**Authority.** Schema-validated, verified against its evidence, consumed by a
state machine you can read in forty lines. One component may request an action.
Halting is human-tier.

Final line, delivered slowly:

> **"If the model is unavailable, malformed, contradictory or simply wrong, the
> worst outcome this system can reach is a refusal to act."**

### Ch 16 — Closing — 19:51 (0:53)

Five layers, five modules. Then the app's own Presenter Guide (a nice touch: the
product ships its own demo script, mapping each scene to the module that
guarantees it).

Land the three lines with a beat between each:

> **Agents investigate.**
> **The Critic challenges.**
> **Deterministic policy decides.**

Stop talking. Do not add a summary after them.

---

## Q&A — likely questions from a technical audience

**"The critic is mocked. Does any of this hold with a real model?"**
Every guarantee is enforced on the harness side, not the model side: strict
`RiskMatrix` validation with `extra="forbid"`, the Verifier's three checks, the
gate, the controller's rule order, the gateway's tier. Swap in OpenRouter and the
same refusals fire. The corrupt-output scene is literally a real model's worst
case, injected deliberately, through the same validation path.

**"What stops the model from just being right, and the harness blocking a good
action?"**
Nothing — and that is the intended trade. The system is asymmetric on purpose: its
worst failure mode is refusing to act, which for a cold chain costs a human
looking at a screen. The inverse design's worst failure mode is spoiled cargo or a
disabled cooling unit.

**"Why not let the LLM output a confidence score?"**
Because a self-reported confidence is not an observation of anything. Confidence
here is computed from what the system can independently verify: how much expected
evidence survived the gate, whether the verifier passed, the gate's exclusion
ratio, the correlation conflicts, and the vehicle's history. The schema rejects
output containing a `confidence` field.

**"Isn't the Correlation Engine doing the model's job?"**
Partly, deliberately. Anything expressible as a deterministic physical check
belongs in code, where it is testable and cheap. The model exists for the residual
— synthesising several signals into a risk judgement with a written rationale. The
correlation result also gives the Verifier something to check the model against.

**"How is 'the agent can't act' enforced, really?"**
By absence, not by policy. `agents.py` has no import of `actions.py`;
`security.py` re-derives that from the module's AST at runtime and probes seven
attack-shaped attributes on a live agent instance. `tests/test_isolation.py`
asserts it. The Tool Registry additionally scopes tools per agent at call time.

**"What happens on a mid-demo restart?"**
The store is append-only SQLite on disk. Decisions, evidence snapshots, actions
and the audit trail all survive a restart; replay works against a cold process.

**"Two policy packs is not really 'domain-independent'."**
Fair. The claim being demonstrated is narrower and checkable: the gate, the
correlation engine, the verifier and the controller contain **no cold-chain
constants** — the second pack proved that by changing the required signals, the
expected-signal denominator, the conflict rules and the reasoning function without
touching any of them.

**"Why is 'execute' just creating a record?"**
Because nothing here should touch a real fleet. `actions.py` documents the
production gateway as a `[FUTURE]` seam behind scoped credentials. The demonstrated
part — request, tiering, human approval, immutable transition log — is the part
that has to be right before that seam is filled.

---

## Recovery drills

| Symptom | Cause | Fix, live |
|---|---|---|
| Every run returns "Circuit Breaker is OPEN" | tripped in Chapter 10 | wait out the 30 s cooldown, run once; it half-opens then closes |
| Confidence reads 33 % instead of 56 % on the killed-agent run | world still on `compound_risk` | click **Normal conditions** first |
| Tyre Safety run shows a halt | breaker still open, or pack never switched | check the ACTIVE badge on the pack card |
| Nothing pending to approve in Ch 9 | Ch 8's run did not halt | re-run the Risk Anomaly scene |
| Dashboard all zeros | fresh store | run two checks; the app also self-seeds on first load |
| Incident Memory still empty in Ch 13 | no halts happened | run the Risk Anomaly scene once |
| Trend says "not enough runs" | fewer than two runs for that signal | run twice more |
| UI looks stale | poll interval | the dashboard polls every 1.5 s; the speed selector divides that |

**Nuclear option, mid-demo:** `POST /simulate/reset` clears the world *and the
store*, then two runs rebuild a clean baseline in about three seconds. You lose
incident history, so avoid it after Chapter 8.

---

## Do not say

Accuracy notes — each of these was checked against the implementation.

- ❌ "The AI decides when to halt." → ✅ The AI produces a risk assessment; the
  Controller decides.
- ❌ "Confidence drops to zero when an agent dies." → ✅ It drops to the share of
  expected evidence that survived. On a healthy world: **56 %** with the
  Environment Agent down (5 of 9 signals), **44 %** with the Vehicle Agent down
  (4 of 9). The walkthrough kills the Environment Agent, so the number on screen
  is 56 %; the app's built-in Presenter Guide kills the Vehicle Agent, so its
  card reads 44 %.
- ❌ "The halt is 100 % confidence." → ✅ 78 %. A contradiction *lowers* confidence;
  it does not raise it.
- ❌ "The system executes a cooling override." → ✅ It creates an escalation record
  after a human approves.
- ❌ "The Verifier re-runs the model." → ✅ It runs three deterministic checks on the
  model's output against the trusted evidence.
- ❌ "The Circuit Breaker retries." → ✅ The Retry Engine retries; the breaker stops
  the call being attempted.
- ❌ "Tyre Safety catches a tyre failure in the demo." → ✅ The demo shows the pack
  changing what is *required*, what is *excluded*, the denominator, and the
  reasoning function. The shipped world states do not produce a tyre blowout
  scenario.
- ❌ "$85,000 of cargo was saved." → ✅ That figure is the counterfactual card's
  illustration of what an unconstrained design could cost.
