# Fleet-Harness — Hackathon Pitch

**AI Tinkerers × Michelin Pune — Harness Engineering Hackathon**

Everything needed for the demo slot and the submission form. Two scripts:
a **live walkthrough (~2:35)** and a **submission cut (~1:50)**, both structured
**problem → harness → proof → close**.

---

## Read of the brief

| Their ask | Our answer |
|---|---|
| Domain | **Operations & Compliance** — a Quality / Incident-Review harness for cold-chain dispatch |
| "Multiple agents, each scoped" | 2 observer agents with **code-enforced disjoint scopes** + a Critic with no tools and no authority |
| "Does it reliably deliver across edge cases?" | 6 failure modes, each degrading to a safe state, each backed by a test |
| Michelin relevance | Fleet safety. And the policy pack switches live to **tyre pressure + heat** — their actual product |

**The single sentence to land:** *Intelligence is advisory. Deterministic policy
is authoritative.*

Their own tip says a harness that handles failure gracefully beats a polished
happy path. So the happy path gets **13 seconds** — including a deliberate
silent beat to let the panel sweep green — and contradiction, failure and the
blocked-action probe get **75 between them**. That is deliberate.

Section 2 discharges their demo rule *"explain what each agent does and why its
scope is constrained"* — stated up front, then proved by everything after it.

---

## Pre-flight (do this 3 minutes before you present)

> ⚠️ **Found and fixed while checking this script:** `backend/.env` had a live
> OpenRouter key with `FORCE_MOCK_CRITIC=false`. A real model call took
> **35–76 seconds per run** in testing — that would silently wreck the timing
> of every "Run check" below. **I've set `FORCE_MOCK_CRITIC=true`** in
> `backend/.env` so runs stay instant. Confirm this before you go on stage — the
> first checklist item catches it if it ever flips back.

```bash
cd backend && python -m uvicorn app.main:app --port 8000
cd frontend && npm run dev
curl -s -X POST http://localhost:8000/simulate/reset
curl -s -X POST http://localhost:8000/runs
curl -s -X POST http://localhost:8000/runs
```

- [ ] **`GET /health` returns `"critic_backend": "mock"`.** If it says
      `"openrouter"`, every run will take 30–75 s — set `FORCE_MOCK_CRITIC=true`
      in `backend/.env` and restart the backend before anything else.
- [ ] Browser 1920×1080, zoom 100 %, view mode **Simple**
- [ ] Active policy pack is **Cold Chain** (check the ACTIVE badge on `/runtime`)
- [ ] Circuit breaker closed — if you tripped it rehearsing, wait 30 s and run once
- [ ] Start on the **Dashboard**, scrolled to the Live Execution panel

---

## Two scripts, not one

The live slot is 3–5 minutes; the submitted video must be 2 minutes. Those want
different things, so there are two scripts below — the submission cut is the
**proof sequence** with the explanation compressed, not the live script read
faster. It still covers every scored beat, including the Michelin-specific
policy-pack switch (see the build note under Script B).

| | Live show-and-tell | Submission video |
|---|---|---|
| Length | **2:32–2:41** (418 words) | **~2:05** (306 words, measured — see build note below) |
| Job | explain *and* prove, then take questions | prove, fast, still complete |
| Cut | nothing — Script B keeps every scored beat, just compressed | live-only beats: none currently; both scripts cover the full checklist |

**Five things the judge must remember.** Everything below serves these:

1. Two agents have separate responsibilities.
2. Their evidence is validated before anything reasons over it.
3. The Critic challenges the evidence.
4. The Verifier checks the Critic.
5. **Deterministic policy — not the AI — controls the outcome.**

---

## Script A — Live show-and-tell · ~2:35

**problem → harness → healthy → contradiction → failure → blocked → policy → close**

Narration is verbatim. **Bold** = the phrase that scores. Speak *over* the click,
never after it. Nothing here is a slide.

### 1 · The problem · 0:00–0:21

*On screen: Dashboard, top.*

| Do | Say |
|---|---|
| Sit still | "When AI makes operational decisions, **intelligence isn't the hard part — trust is.** This is a refrigerated shipment; cargo spoils outside two to six degrees, and a wrong call loses the load. The tempting fix — let a model watch the telemetry and decide — **fails three ways: bad data trusted, bad reasoning trusted, and the model handed authority.**" |

### 2 · The harness · 0:21–0:54

*Scroll to the **5-Layer Decision Pipeline Architecture** strip and point at each
box as you name it. Use the labels the screen already shows — do not invent a
second set of five.*

| Do | Say |
|---|---|
| Scroll to the strip | "So we built **a harness, not an agent** — five stages, each its own module." |
| Layer 1 | "Two observer agents, **isolated in code, not by prompt**: Vehicle reads only the truck's sensors, Environment only route and weather." |
| Layer 2 | "A Trust Gate that decides which evidence is admissible." |
| Layer 3 | "The Critic — **the only LLM here, no tools, no action function** — and a Verifier that **independently checks the Critic's claims against the trusted evidence**." |
| Layers 4–5 | "Then a deterministic Controller: **the only component allowed to request an action**, and a gateway that requires a human to release it." |

### 3 · Healthy run · 0:54–1:07

*This is the one place in the script with a deliberate silence. The Live
Execution panel sweeps through Vehicle Agent → Environment Agent → Trust Gate →
Risk Assessment Engine → Decision Authority in about a second, each turning
green in order. Let the judges watch it happen — don't narrate every node.*

| Do | Say |
|---|---|
| **Healthy** → **Run check** | "Run a normal shipment." |
| *(pause ~2 s — say nothing; let the flow sweep through and settle)* | — |
| Panel settled on green | "Every stage agrees — **auto-optimise, a hundred percent confidence.**" |

### 4 · The contradiction — your hero scene · 1:07–1:51

*Slow down here. This is the scene the whole pitch is built around.*

| Do | Say |
|---|---|
| **Risk Anomaly** → **Run check** | "Now the edge case. The cooling unit reports ON — while cargo climbs to **eleven and a half degrees. Both cannot be true.**" |
| Point at the two agent nodes | "Both agents observed that independently — neither can explain the other's data away." |
| Scroll to the trace timeline. **Point at step 4, "Evidence Correlation," then step 5, "Risk Assessment Engine" — the numbers themselves show the order.** | "Correlation catches the physical impossibility **before the model reasons at all** — you can see it: step four, before the Critic ever runs at step five. The Critic then finds the contradiction. The Verifier **independently checks the Critic's claims against the trusted evidence — one component auditing another.**" |
| Point at confidence | "Confidence falls from a hundred to **seventy-eight percent — computed in code, never self-reported by the model.**" |
| Banner / approval card | "**The Critic did not decide this — it produced an assessment; a deterministic rule decided.** The system **requests a human-tier escalation; it does not execute the action itself.**" |

### 5 · Failure · 1:51–2:07

*Simulation Lab. Click **Normal conditions**, then **Disconnect route sensors** →
**Run check**. One failure, shown properly — beats three failures shown in a blur.*

| Do | Say |
|---|---|
| Kill the agent → **Run check** | "Now break it. Kill the Environment Agent mid-route. **The harness doesn't guess the missing half** — insufficient data, **fifty-six percent**, no action taken. Malformed model output and stale evidence take the same path: refused, no crash." |

### 6 · The agents cannot act · 2:07–2:22

| Do | Say |
|---|---|
| **Security Check** → **Test the safety lock** | "And the agents cannot act. This probe **really** tries eight paths from an agent to a dispatch action — **all eight blocked.** The agents module has no import of the actions module. **There is nothing to call.**" |

### 7 · Policy + close · 2:22–2:36

| Do | Say |
|---|---|
| `/runtime` → click **Tyre Safety** | "**The runtime stays the same; only the domain policy changes** — cold chain to tyre safety, zero code changes." |
| Face the judges | "**A single agent can't audit its own reasoning, can't deny itself authority, and can't degrade safely when it fails. That's why this needed a harness.** Agents investigate. The critic challenges. Deterministic policy decides." |

> Say nothing after the last line. Let it sit.

---

## Script B — Submission video · ~2:30 (video: `demo/ColdChain-Harness-Demo.mp4`)

**Rebuilt against the redesigned app** — the old scene-preset buttons and the
5-layer strip are gone from the Dashboard. The operator now submits real
telemetry through a **Shipment Evaluation form** (a "Scenario" preset picker
plus real cargo/ambient/cooling/policy fields), which flows straight into the
new **Live Runtime Pipeline** — 8 stages, animated live from the real trace.
This cut also adds one thing the earlier draft only asserted: a **live
Verifier → Critic feedback loop**. Armed via Advanced Demo Controls, it makes
the Critic's first pass genuinely get rejected, revise, and pass on
recheck — visible as a real **"↺ fed back & revised"** badge on the Verifier
stage, not a claim. This table is the exact narration `create_demo.py` speaks;
every row is one beat, one audio clip, one real API call.

**Every "we chose this option" moment is ringed on screen, not just spoken.**
A judge shouldn't have to hunt a small form field while the voiceover claims
something about it — so the Scenario field, the Cooling/Cargo Temperature
fields, the Policy Pack field, and the specific Environment Agent stage all
get a highlight ring (a dimmed background + a blue outline, the same
mechanism already used to ring the pipeline stages and result cards) at the
exact moment the narration references them.

| Beat | On screen | Say |
|---|---|---|
| b01 | Dashboard | "When AI makes operational decisions, **intelligence isn't the hard part — trust is.** Cargo here spoils outside two to six degrees." |
| b02 | (same shot) | "A model deciding alone **fails three ways: bad data trusted, bad reasoning trusted, authority handed away.**" |
| b03 | Live Runtime Pipeline card | "So: **a harness, not an agent.**" |
| b04 | Vehicle Agent → Environment Agent stages | "Two observer agents **isolated in code**: Vehicle sees only the truck, Environment only route and weather." |
| b05 | Trust Gate stage | "A Trust Gate decides what evidence is admissible." |
| b06 | Risk Assessment Engine → Verifier stages | "The Risk Assessment Engine — **the only LLM, no tools, no action function** — audited by a Verifier." |
| b07 | Decision Authority stage | "Then a deterministic Decision Authority: **the only component allowed to request an action.**" |
| b08 | Scenario field **ringed** on "Healthy Shipment" → **Evaluate Shipment** | "Run a normal shipment through the real harness — the same agents, the same Trust Gate, the same deterministic controller that grades every check on this system, live." |
| b09 | Final Decision card | "Every stage agrees — **auto-optimise, a hundred percent confidence.**" |
| b10 | Advanced Demo Controls; **↺ Verifier Feedback Loop** button ringed, then clicked *(armed quietly, before the next run)* | "Now the edge case." |
| b11 | Scenario: **Sensor Contradiction**; Cooling Status field ringed, then Cargo Temperature field ringed (showing **11.5**) | "Cooling reports ON while cargo climbs to **eleven and a half degrees — both cannot be true.**" |
| b12 | (same shot) | "Both agents observed it independently." |
| b13 | **Evaluate Shipment** | "Run it — the exact same seven stages execute again, in the exact same order, but this time the evidence disagrees with itself." |
| b14 | Evidence Correlation stage | "Correlation catches it deterministically — Evidence Correlation runs before the Critic ever does." |
| b15 | Verifier stage *(the "fed back & revised" badge is live here)* | "The Verifier rejects the first pass, feeds its reason back. The Critic revises; the recheck passes clean." |
| b16 | Final Decision card | "Confidence falls to **seventy-eight percent — computed in code, never self-reported.**" |
| b17 | Human Approval card | "**The Critic did not decide this — a deterministic rule did.** It **requests a human-tier escalation, not an execution.**" |
| b18 | Scenario field **ringed** on "Missing Sensor" | "Break it: kill the Environment Agent." |
| b19 | **Evaluate Shipment** → Environment Agent stage **ringed** (shows "✕ Rejected") → Final Decision card | "The harness doesn't guess the missing half. It waits for the run to finish grading what it actually has: insufficient data, **fifty-six percent**, no action taken." |
| b20 | (same shot) | "The same path handles malformed output and stale evidence." |
| b21 | *(navigate to Simulation Lab)* | "And the agents cannot act." |
| b22 | Security Check → **Test the safety lock** → **Show how we tested this** | "Eight paths from an agent to a dispatch action, all eight blocked — **nothing to call.**" |
| b23 | *(back to Dashboard)* Scenario: **Healthy Shipment** | "**The domain is data, not code.**" |
| b24 | Policy Pack field **ringed** on "Tyre Safety" the instant it's set | "Switch to tyre safety and the signals and risk logic change." |
| b25 | **Evaluate Shipment** | "Zero code changes in the gate, the critic, or the controller — while this new run finishes executing under the new policy." |
| b26 | Back to Dashboard, scroll to top | "**A single agent can't audit its own reasoning, can't deny itself authority, and can't degrade safely when it fails.**" |
| *(end card)* | — | "Agents investigate. The critic challenges. Deterministic policy decides." |

---

## Numbers you will say — deliberately only four

Every extra number costs the judge attention they should be spending on the
architecture. These four each *prove* something; everything else moved to Q&A.

| Number | Proves |
|---|---|
| **11.5 °C** with cooling ON | makes the contradiction concrete and physical |
| **78 %** | confidence is computed, not fabricated — it *fell*, and by a stated rule |
| **56 %** | graceful degradation is real, not a slogan |
| **8 / 8 blocked** | isolation is structural, not a permission setting |

**Do not say in narration:** "four factors", "nine signals" (more than once),
"eighty-nine percent", "ninety-eight tests". They are true, they are in the
submission text, and they are ready in Q&A — but spoken aloud they blur the four
above.

<details>
<summary>Full verified set, for Q&A</summary>

| Moment | Value | Why |
|---|---|---|
| Healthy | `AUTO_OPTIMIZE` 100 % | 9 / 9 trusted, no contradiction |
| Contradiction | `CRITICAL_HALT` 78 % | (9 trusted − 2 contradiction penalty) ÷ 9 |
| Corrupt output | `INSUFFICIENT_DATA` 100 % | evidence complete; refused on the *reasoning* axis |
| Agent killed (route sensors) | `INSUFFICIENT_DATA` 56 % | 5 of 9 signals survived |
| Agent killed (truck sensors) | `INSUFFICIENT_DATA` 44 % | 4 of 9 — the dashboard's "Kill Agent A" button |
| Stale reading | `INSUFFICIENT_DATA` 89 % | 8 of 9 trusted; required signal excluded |
| Network blip | recovers in-run | RetryEngine, `retries: 1` |
| Red-team probe | 8 / 8 blocked | 7 attribute probes + the import-graph check |
| Test suite | 98 passed | |

</details>

> ⚠️ **The retry does not apply to a killed agent.** The RetryEngine wraps only
> the Critic's backend call — the one thing that crosses a network boundary. An
> unavailable agent is recorded as failed immediately, with no retry. If you draw
> *agent fails → retry → still unavailable*, you are describing behaviour this
> system does not have, and it is exactly the kind of claim a judge will probe.
> Retry belongs to the **network-blip** scenario; keep it for Q&A.

---

## How each beat scores

| Criterion | Weight | Beats that earn it |
|---|---|---|
| **Harness Design** | 30 % | **§2** (every role and its constraint, stated) · §4 (Verifier checking the Critic; controller the only thing that may act) · §7 (policy as data) |
| **Reliability** | 25 % | §5 (killed agent → safe degradation) · §4 (contradiction handled, not crashed) · "refused, no crash" |
| **Domain Relevance** | 25 % | **§1** (cold-chain spoilage — a real loss) · §4 (human escalation before dispatch stops) · **§7 (tyre safety — Michelin's own product)** |
| **Demonstration** | 20 % | Every claim is a live click on a running system; no slides; the numbers on screen are the numbers you say |

### Their "what makes a good harness" checklist

| Their criterion | Where it lands |
|---|---|
| Clear agent roles with defined scope | **§2** — every role named with its constraint; §6 proves it |
| Constraints that prevent failure modes | §4 — schema `extra="forbid"`, Trust Gate; §6 — no import path to actions |
| Feedback loops between agents | §4 — **Verifier checks the Critic's claims**; Correlation pre-checks before the model reasons |
| State/memory across steps | `RunState` per run; audit trail; Incident Memory — *say this in Q&A, don't spend demo time* |
| Graceful degradation | §5 — the killed agent lands in `INSUFFICIENT_DATA`, never a crash |

---

## Submission form — draft answers

**Project name:** Fleet-Harness

**One-sentence description:** A decision-control harness for cold-chain fleet
dispatch, where isolated agents investigate, a critic is audited by a verifier,
and only deterministic policy may authorise an action.

**Domain:** Operations & Compliance

**Workflow — each agent, its role, its constraints:**

> **Vehicle Agent** — reads only the truck's own telemetry (cargo temperature,
> cooling status, tyre pressure/temperature, speed). *Constraint:* holds no
> reference to route data, to the critic, or to any action function; cannot call
> another agent's tool (denied at call time by a scoped tool registry).
>
> **Environment Agent** — reads only route and weather context (ambient
> temperature, weather, traffic, dwell). *Constraint:* symmetrically isolated;
> cannot see truck sensors.
>
> **Trust Gate** *(deterministic, not an agent)* — grades every reading in four
> sub-stages: schema, freshness recomputed from the timestamp, provenance against
> the one authorised source agent, and normalization to one reading per signal.
> *Constraint:* stale, wrong-source or unknown signals are **excluded**, not
> down-weighted.
>
> **Correlation Engine** *(deterministic)* — checks physical consistency *before*
> the model reasons (e.g. cooling ON while cargo is above the safe band).
>
> **Risk Assessment Engine (Critic)** — the only LLM in the path. Receives
> structured, already-gated evidence. *Constraints:* no tools, no world state, no
> action function; output must pass strict schema validation (`extra="forbid"`)
> or it is rejected outright; **forbidden from reporting a confidence value**.
>
> **Verifier** — audits the Critic against its own evidence: self-consistency,
> evidence grounding, and whether a claimed contradiction is actually supported.
> This is the harness's feedback loop.
>
> **Deterministic Controller** — a three-state machine (`AUTO_OPTIMIZE`,
> `INSUFFICIENT_DATA`, `CRITICAL_HALT`), five rules, first match wins. Confidence
> is computed here in code, with a fixed denominator so data loss genuinely lowers
> it. *Constraint:* it is the **only** component permitted to request an action.
>
> **Action Gateway** — tiers every action. Halting dispatch is HUMAN tier: it
> opens for approval and waits for a person, then writes an immutable escalation
> record. Every transition lands in an append-only audit log.
>
> **Policy Engine** — the domain (required signals, thresholds, contradiction
> rules, reasoning) is a swappable pack, not code. Cold Chain and Tyre Safety
> ship today.

**Demo video:** `demo/ColdChain-Harness-Demo.mp4` — currently 3:20, and the form
asks for 2 minutes. Either cut that video's own Act 3 (the isolation section), or
re-run `python create_demo.py` with its beat table replaced by this script, which
is already timed to fit.

---

## Q&A prep

**"Is the LLM real, or mocked?"**
Mocked by default so the demo never depends on the network — and I'll say that
up front rather than have you find it. Every guarantee you saw is enforced on the
*harness* side: schema validation, the verifier, the gate, the controller's rule
order. Point it at OpenRouter and the same refusals fire. The corrupt-output scene
*is* a real model's worst case, injected deliberately through the same validation
path.

**"Why not just prompt the model to be careful?"**
Because a prompt is a request and a harness is a constraint. The agents can't
reach each other's data — not because we asked them not to, but because there is
no reference. `agents.py` has no import of `actions.py`; the probe proves it at
runtime and a test fails the build if anyone adds one.

**"What if the model is right and the harness blocks a good action?"**
That's the trade, deliberately. The system is asymmetric: its worst failure is
refusing to act, which costs a human looking at a screen. The inverse design's
worst failure is spoiled cargo or a disabled cooling unit.

**"Isn't the Correlation Engine doing the model's job?"**
Partly, on purpose. Anything expressible as a deterministic physical check
belongs in code where it's testable and free. The model handles the residual —
synthesising several signals into a judgement with a rationale. And the
correlation result gives the Verifier something to check the model against.

**"How does it remember anything?"**
`RunState` is one object per run that every stage reads and writes. Across runs,
a trend engine tracks each signal's history, and Incident Memory joins past halts
with how each was resolved and by whom. All of it replayable from an append-only
store.

**"What's the hardest part you got wrong first?"**
Confidence. The first version divided by the number of signals we *received*, so
killing an agent left us at 100 % confidence in a smaller picture. It's now a
fixed denominator — the signals a healthy fleet produces — so losing an agent
genuinely lowers the number. Property-based fuzzing also caught confidence
exceeding 1.0 when an agent emitted a duplicate reading; the gate now keeps one
reading per signal.

---

## If you are running long or short

**Running long (cut in this order):**
1. §7's tyre pack switch → say the sentence, skip the click *(saves 9 s)*
2. §4's "both agents observed that independently" line *(saves 6 s)*
3. §2's Trust Gate line — fold it into the Critic line *(saves 5 s)*

**Never cut:** §2 (it is 30 % of the score on its own), the contradiction in §4,
the Verifier-checks-the-Critic line, the "a deterministic rule decided" line, or
the probe in §6.

**Running short — add in this order:**
1. Network blip → Retry Engine recovers inside the same run *(+12 s)* — note this
   is the **only** scenario where retry applies
2. Circuit breaker: three failures and it stops attempting the call at all *(+12 s)*
3. Audit page: select any past run and reconstruct the whole decision *(+15 s)*
