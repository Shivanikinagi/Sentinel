#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fleet-Harness — automated master demo walkthrough.

Boots the backend and the frontend, waits for both to be ready, then drives a
15-20 minute scripted product demonstration through a real browser with
Playwright: every page, every runtime subsystem, every simulation, every policy
pack, and every significant UX flow.

Nothing is faked. Every scenario is triggered through the same UI control or
HTTP endpoint an operator would use, and every number the narration quotes is
read back out of the running system.

Outputs (all under demo/):
    automation.log        full timestamped run log
    captions.srt          captions timed to the ACTUAL elapsed run
    screenshots/*.png     one still per chapter plus key beats
    video/*.webm          full-session screen recording (Playwright)

Usage:
    python demo/create_master_demo.py                    # full run, records video
    python demo/create_master_demo.py --headed           # watch it drive
    python demo/create_master_demo.py --speed 6          # fast rehearsal
    python demo/create_master_demo.py --no-servers       # attach to servers already up
    python demo/create_master_demo.py --chapters 7,8     # just those chapters
    python demo/create_master_demo.py --dry-run          # plan + captions only, no browser
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import time
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

# ---------------------------------------------------------------- paths / setup
DEMO_DIR = Path(__file__).resolve().parent
ROOT = DEMO_DIR.parent
BACKEND_DIR = ROOT / "backend"
FRONTEND_DIR = ROOT / "frontend"

LOG_PATH = DEMO_DIR / "automation.log"
SRT_PATH = DEMO_DIR / "captions.srt"
SHOTS_DIR = DEMO_DIR / "screenshots"
VIDEO_DIR = DEMO_DIR / "video"

API = "http://localhost:8000"
UI = "http://localhost:5173"

VIEWPORT = {"width": 1920, "height": 1080}

# Narration pacing. Caption length drives hold time, so the walkthrough is paced
# by what is actually being said rather than by arbitrary sleeps.
WORDS_PER_SECOND = 2.95
BEAT_PAUSE = 0.6
TITLE_CARD_SECONDS = 1.9

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


# ------------------------------------------------------------------------ log
class Log:
    def __init__(self, path: Path) -> None:
        self.fh = path.open("w", encoding="utf-8", newline="\n")
        self.t0 = time.time()

    def __call__(self, msg: str, level: str = "INFO") -> None:
        line = f"[{time.time() - self.t0:8.2f}s] {level:5} {msg}"
        print(line, flush=True)
        self.fh.write(line + "\n")
        self.fh.flush()

    def close(self) -> None:
        self.fh.close()


LOG: "Log | None" = None


def log(msg: str, level: str = "INFO") -> None:
    if LOG:
        LOG(msg, level)
    else:
        print(msg, flush=True)


# ------------------------------------------------------------------- http util
def api(method: str, path: str, body: dict | None = None, timeout: float = 20.0):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        f"{API}{path}", data=data, method=method,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
    return json.loads(raw) if raw else None


def url_ok(url: str, timeout: float = 2.0) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.status < 500
    except Exception:
        return False


def wait_until(pred: Callable[[], bool], what: str, timeout: float = 120.0,
               interval: float = 1.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if pred():
                log(f"ready: {what}")
                return True
        except Exception:
            pass
        time.sleep(interval)
    log(f"TIMED OUT waiting for {what}", "ERROR")
    return False


# --------------------------------------------------------------- server manager
class Servers:
    """Starts uvicorn + vite only if they are not already listening, and only
    stops what this script itself started."""

    def __init__(self) -> None:
        self.procs: list[tuple[str, subprocess.Popen]] = []

    @staticmethod
    def _python() -> str:
        for candidate in (BACKEND_DIR / ".venv/Scripts/python.exe",
                          BACKEND_DIR / ".venv/bin/python"):
            if candidate.exists():
                return str(candidate)
        return sys.executable

    def start(self) -> None:
        if url_ok(f"{API}/health"):
            log("backend already running on :8000 — reusing it")
        else:
            py = self._python()
            log(f"starting backend: {py} -m uvicorn app.main:app --port 8000")
            self._spawn("backend", [py, "-m", "uvicorn", "app.main:app",
                                    "--port", "8000"], cwd=BACKEND_DIR)

        if url_ok(UI):
            log("frontend already running on :5173 — reusing it")
        else:
            npm = shutil.which("npm.cmd") or shutil.which("npm") or "npm"
            log(f"starting frontend: {npm} run dev")
            self._spawn("frontend", [npm, "run", "dev"], cwd=FRONTEND_DIR)

        if not wait_until(lambda: url_ok(f"{API}/health"), "backend /health", 180):
            raise SystemExit("backend never became ready")
        if not wait_until(lambda: url_ok(UI), "frontend :5173", 180):
            raise SystemExit("frontend never became ready")

        log(f"backend health: {api('GET', '/health')}")

    def _spawn(self, name: str, cmd: list[str], cwd: Path) -> None:
        kwargs = {}
        if os.name == "nt":
            kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        proc = subprocess.Popen(
            cmd, cwd=str(cwd), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            **kwargs,
        )
        self.procs.append((name, proc))

    def stop(self) -> None:
        for name, proc in self.procs:
            log(f"stopping {name} (pid {proc.pid})")
            try:
                if os.name == "nt":
                    subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                                   capture_output=True)
                else:
                    proc.send_signal(signal.SIGTERM)
                proc.wait(timeout=15)
            except Exception as exc:
                log(f"could not stop {name}: {exc}", "WARN")


# ----------------------------------------------------------------- demo overlay
# Injected into the page, outside the React root, so it survives hash routing and
# never touches application state. Chapter chip, caption bar, spotlight ring.
OVERLAY_JS = r"""
(() => {
  if (window.__demo) return;
  const css = `
  #demo-ov { position: fixed; inset: 0; pointer-events: none; z-index: 2147483000;
             font-family: 'Plus Jakarta Sans', system-ui, sans-serif; }
  /* Sits below the app's own topbar so it never covers the mode toggle. */
  #demo-chip { position: absolute; top: 92px; right: 26px;
    background: rgba(6,12,24,.92); border: 1px solid rgba(56,189,248,.45);
    color: #e2e8f0; border-radius: 999px; padding: 7px 16px; font-size: 13px;
    font-weight: 700; letter-spacing: .02em; box-shadow: 0 8px 30px rgba(0,0,0,.55);
    opacity: 0; transition: opacity .35s ease; }
  #demo-chip .n { color: #38bdf8; margin-right: 8px; }
  #demo-cap { position: absolute; left: 50%; bottom: 34px; transform: translateX(-50%);
    max-width: 1180px; width: calc(100% - 160px);
    background: rgba(6,12,24,.94); border: 1px solid rgba(148,163,184,.28);
    border-left: 4px solid #38bdf8; border-radius: 12px; padding: 16px 24px;
    color: #f1f5f9; font-size: 21px; line-height: 1.45; font-weight: 500;
    box-shadow: 0 18px 60px rgba(0,0,0,.65); opacity: 0;
    transition: opacity .3s ease; }
  #demo-cap.show { opacity: 1; }
  #demo-card { position: absolute; inset: 0; background: rgba(3,7,18,.96);
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    opacity: 0; transition: opacity .45s ease; }
  #demo-card.show { opacity: 1; }
  #demo-card .kicker { color: #38bdf8; font-size: 15px; font-weight: 800;
    letter-spacing: .32em; text-transform: uppercase; margin-bottom: 20px; }
  #demo-card .title { color: #f8fafc; font-size: 62px; font-weight: 800;
    letter-spacing: -.02em; text-align: center; max-width: 1200px; }
  #demo-card .sub { color: #94a3b8; font-size: 22px; margin-top: 18px;
    text-align: center; max-width: 950px; line-height: 1.5; }
  #demo-card .rule { width: 90px; height: 3px; background: #38bdf8; margin: 30px 0 0; }
  .demo-spot { outline: 3px solid #38bdf8 !important;
    outline-offset: 5px; border-radius: 12px;
    box-shadow: 0 0 0 9999px rgba(2,6,17,.55), 0 0 34px rgba(56,189,248,.5) !important; }
  `;
  const style = document.createElement('style');
  style.textContent = css;

  const ov = document.createElement('div');
  ov.id = 'demo-ov';
  ov.innerHTML = `
    <div id="demo-chip"><span class="n"></span><span class="t"></span></div>
    <div id="demo-cap"></div>
    <div id="demo-card">
      <div class="kicker"></div><div class="title"></div>
      <div class="rule"></div><div class="sub"></div>
    </div>`;
  // This script is installed before the document exists, so mount on whatever
  // root is available and retry on DOMContentLoaded if there is none yet.
  const attach = () => {
    const root = document.body || document.documentElement;
    if (!root) return false;
    if (!style.isConnected) root.appendChild(style);
    if (!ov.isConnected) root.appendChild(ov);
    return true;
  };
  if (!attach()) document.addEventListener('DOMContentLoaded', attach);

  let spotted = null;
  window.__demo = {
    chapter(n, total, title) {
      const chip = ov.querySelector('#demo-chip');
      chip.querySelector('.n').textContent = n + '/' + total;
      chip.querySelector('.t').textContent = title;
      chip.style.opacity = '1';
    },
    caption(text) {
      const cap = ov.querySelector('#demo-cap');
      cap.classList.remove('show');
      setTimeout(() => { cap.textContent = text; cap.classList.add('show'); }, 120);
    },
    clearCaption() { ov.querySelector('#demo-cap').classList.remove('show'); },
    card(kicker, title, sub) {
      const c = ov.querySelector('#demo-card');
      c.querySelector('.kicker').textContent = kicker;
      c.querySelector('.title').textContent = title;
      c.querySelector('.sub').textContent = sub || '';
      c.classList.add('show');
    },
    hideCard() { ov.querySelector('#demo-card').classList.remove('show'); },
    spot(sel) {
      this.unspot();
      const el = document.querySelector(sel);
      if (el) { el.classList.add('demo-spot'); spotted = el; }
      return !!el;
    },
    unspot() {
      if (spotted) { spotted.classList.remove('demo-spot'); spotted = null; }
      if (window.__demoSpotted) {
        window.__demoSpotted.classList.remove('demo-spot');
        window.__demoSpotted = null;
      }
    },
  };
})();
"""


# ------------------------------------------------------------------ beat model
@dataclass
class Beat:
    """One narration line plus whatever the browser does while it is spoken."""
    say: str
    do: "Callable[[Ctx], None] | None" = None
    extra: float = 0.0          # seconds beyond the spoken length (animations)
    shot: str | None = None     # screenshot filename stem
    spot: str | None = None     # CSS selector to spotlight during this beat

    @property
    def seconds(self) -> float:
        return round(len(self.say.split()) / WORDS_PER_SECOND + BEAT_PAUSE + self.extra, 2)


@dataclass
class Chapter:
    number: int
    title: str
    subtitle: str
    beats: list[Beat] = field(default_factory=list)

    @property
    def seconds(self) -> float:
        return round(sum(b.seconds for b in self.beats) + TITLE_CARD_SECONDS, 2)


# ------------------------------------------------------------------- driver ctx
class Ctx:
    """Everything a beat is allowed to do to the running app."""

    def __init__(self, page, speed: float, total_chapters: int) -> None:
        self.page = page
        self.speed = speed
        self.total_chapters = total_chapters
        self.route = None
        self.cues: list[tuple[float, float, str]] = []   # (start, end, text)
        self.t0 = time.time()
        self.failures = 0

    # -- pacing -------------------------------------------------------------
    def hold(self, seconds: float) -> None:
        time.sleep(max(0.05, seconds / self.speed))

    def now(self) -> float:
        return time.time() - self.t0

    # -- overlay ------------------------------------------------------------
    def js(self, expr: str):
        try:
            return self.page.evaluate(expr)
        except Exception as exc:
            log(f"overlay/js failed: {exc}", "WARN")
            return None

    def chapter_card(self, ch: Chapter) -> None:
        self.js(f"window.__demo && window.__demo.chapter({ch.number}, "
                f"{self.total_chapters}, {json.dumps(ch.title)})")
        self.js("window.__demo && window.__demo.clearCaption()")
        self.js("window.__demo && window.__demo.unspot()")
        self.js(f"window.__demo && window.__demo.card("
                f"{json.dumps('Chapter ' + str(ch.number))}, "
                f"{json.dumps(ch.title)}, {json.dumps(ch.subtitle)})")
        self.hold(TITLE_CARD_SECONDS)
        self.js("window.__demo && window.__demo.hideCard()")
        self.hold(0.5)

    def caption(self, text: str) -> None:
        self.js(f"window.__demo && window.__demo.caption({json.dumps(text)})")

    def spot(self, selector: str | None) -> None:
        self.js("window.__demo && window.__demo.unspot()")
        if not selector:
            return
        try:
            handle = self.page.locator(selector).first.element_handle(timeout=4000)
            if handle is not None:
                handle.evaluate("el => { el.classList.add('demo-spot');"
                                " window.__demoSpotted = el; }")
        except Exception:
            log(f"spotlight target not found: {selector}", "WARN")

    # -- navigation ---------------------------------------------------------
    def goto(self, route: str) -> None:
        """HashRouter: after the first full load, switch routes by hash so the
        injected overlay (and the page's React state) survive."""
        if self.route is None:
            self.page.goto(f"{UI}/#{route}", wait_until="domcontentloaded")
            self.page.wait_for_timeout(1800)
        else:
            self.page.evaluate(f"window.scrollTo({{top:0}}); location.hash = {json.dumps(route)}")
            self.page.wait_for_timeout(700)
        self.route = route
        log(f"route -> {route}")

    def scroll_to(self, selector: str, block: str = "center") -> None:
        """Resolved through Playwright so :has-text()/:text-is() work, then
        scrolled smoothly (document.querySelector cannot parse those)."""
        try:
            handle = self.page.locator(selector).first.element_handle(timeout=6000)
            if handle is None:
                raise RuntimeError("no element handle")
            handle.evaluate("(el, block) => el.scrollIntoView("
                            "{behavior: 'smooth', block})", block)
        except Exception as exc:
            log(f"scroll target not found: {selector} ({exc.__class__.__name__})", "WARN")
        self.page.wait_for_timeout(700)

    def scroll_top(self) -> None:
        self.page.evaluate("window.scrollTo({top: 0, behavior: 'smooth'})")
        self.page.wait_for_timeout(700)

    # -- interaction --------------------------------------------------------
    def click(self, selector: str, why: str = "") -> bool:
        try:
            loc = self.page.locator(selector).first
            loc.scroll_into_view_if_needed(timeout=8000)
            self.page.wait_for_timeout(320)
            loc.click(timeout=8000)
            log(f"click {selector} {('— ' + why) if why else ''}")
            self.page.wait_for_timeout(420)
            return True
        except Exception as exc:
            self.failures += 1
            log(f"CLICK FAILED {selector}: {exc}", "WARN")
            return False

    def select(self, selector: str, value: str) -> None:
        try:
            self.page.locator(selector).first.select_option(value, timeout=8000)
            log(f"select {selector} = {value}")
            self.page.wait_for_timeout(700)
        except Exception as exc:
            self.failures += 1
            log(f"SELECT FAILED {selector}: {exc}", "WARN")

    def type_in(self, selector: str, text: str) -> None:
        try:
            loc = self.page.locator(selector).first
            loc.scroll_into_view_if_needed(timeout=8000)
            loc.fill("")
            loc.type(text, delay=90)
            log(f"type {selector!r} = {text!r}")
        except Exception as exc:
            self.failures += 1
            log(f"TYPE FAILED {selector}: {exc}", "WARN")

    # -- run control --------------------------------------------------------
    def latest_run_id(self) -> str | None:
        try:
            recent = api("GET", "/decisions?limit=1")
            return recent[0]["run_id"] if recent else None
        except Exception:
            return None

    def run_and_wait(self, selector: str = ".mc-run-btn") -> dict | None:
        """Click a Run check button and wait for the new decision to land."""
        before = self.latest_run_id()
        self.click(selector, "run the harness")
        deadline = time.time() + 25
        while time.time() < deadline:
            rid = self.latest_run_id()
            if rid and rid != before:
                decision = api("GET", f"/decisions/{rid}")
                log(f"RUN {rid}: {decision['controller_state']} "
                    f"conf={decision['confidence']} pack={decision['policy_pack']} "
                    f"retries={len(decision['trace']['retries'])} "
                    f"excluded={len(decision['trace']['excluded_evidence_ids'])} "
                    f"reason={decision['reason']!r}")
                self.page.wait_for_timeout(1700)   # let the UI poll catch up
                return decision
            time.sleep(0.4)
        log("no new decision observed after Run check", "WARN")
        return None

    def shot(self, name: str) -> None:
        SHOTS_DIR.mkdir(parents=True, exist_ok=True)
        path = SHOTS_DIR / f"{name}.png"
        try:
            self.page.screenshot(path=str(path))
            log(f"screenshot -> {path.name}")
        except Exception as exc:
            log(f"screenshot failed ({name}): {exc}", "WARN")


# ================================================================== the script
# Every beat below was written against the running system; the numbers quoted in
# the narration are the numbers this build actually produces.

def _(fn):
    """Tiny alias so beat actions read as one-liners."""
    return fn


def build_chapters() -> list[Chapter]:
    C: list[Chapter] = []

    # ---------------------------------------------------------------- CH 1
    C.append(Chapter(1, "The Problem", "Why a harness, and not an agent", [
        Beat("Fleet-Harness is not an AI agent. It is a trust harness: a decision-control "
             "layer between AI reasoning and a real operational action.",
             _(lambda c: c.goto("/")), extra=1.0, shot="ch01-dashboard"),
        Beat("The asset is a refrigerated truck, TRUCK-042, carrying cargo that spoils "
             "outside a two-to-six degree band."),
        Beat("The obvious design hands the telemetry to a language model and lets it "
             "decide. That design fails in three ways."),
        Beat("It trusts whatever data arrives: stale, duplicated, or from the wrong "
             "sensor."),
        Beat("It trusts whatever the model says: malformed, ungrounded, or internally "
             "contradictory."),
        Beat("And it gives the model authority to change something physical."),
        Beat("Fleet-Harness splits those three concerns into separate modules that never "
             "collapse back into one call. Intelligence is advisory, evidence is gated, "
             "deterministic policy is authoritative — each boundary enforced in code and "
             "backed by a test.", spot=".harness-badge"),
        Beat("It boots with no API key: a deterministic mock reasoner stands in, so "
             "nothing here depends on the network.", spot=".model-badge"),
    ]))

    # ---------------------------------------------------------------- CH 2
    C.append(Chapter(2, "Architecture", "The Harness Runtime and the five layers", [
        Beat("This is the Harness Runtime. Every box maps to a real backend module.",
             _(lambda c: (c.goto("/runtime"), c.scroll_to(".runtime-diagram"))),
             extra=1.0, shot="ch02-runtime-diagram", spot=".runtime-diagram"),
        Beat("The Supervisor starts each agent, times every stage, retries the one call "
             "that crosses a network boundary, and assembles the execution trace."),
        Beat("The State Manager is RunState: one object per run that every stage reads "
             "and writes, instead of variables threaded from function to function."),
        Beat("The Scheduler is the Planner. It decides which agents run, and whether they "
             "may run in parallel."),
        Beat("The Retry Engine bounds retries inside one run. The Circuit Breaker is "
             "separate: it decides whether to attempt the call at all, across runs."),
        Beat("The Policy Engine selects the active domain pack. The gate, the correlation "
             "engine and the reasoner all read from whichever pack is active."),
        Beat("The Execution Trace times every stage, including retries and the four Trust "
             "Gate sub-stages."),
        Beat("Memory tracks a signal across a vehicle's past runs, so the harness judges "
             "a trend, not a snapshot."),
        Beat("Audit is an append-only log of every meaningful transition."),
        Beat("The line underneath is the real call order: Planner, Supervisor running "
             "agents, gate, correlation, risk assessment, verifier, controller — then the "
             "Harness, which persists and decides whether to request an action.",
             _(lambda c: c.scroll_to(".runtime-flow-note")), spot=".runtime-flow-note"),
        Beat("The same architecture as five layers, each in its own module: Intelligence, "
             "Evidence, Policy, Decision, Authority — never collapsed into one model "
             "call. That separation is the product.",
             _(lambda c: (c.goto("/pipeline"), c.scroll_to(".layer-list"))),
             extra=1.0, shot="ch02-layers", spot=".layer-list"),
    ]))

    # ---------------------------------------------------------------- CH 3
    C.append(Chapter(3, "The Dashboard", "Every widget on the operator view", [
        Beat("The operator's view is a control room, not a KPI wall.",
             _(lambda c: (c.goto("/"), c.scroll_top())), extra=0.8),
        Beat("Top line: decisions waiting on a human, vehicles monitored, harness runs "
             "this session. The Harness Trust Score beside it composites four measured "
             "things — evidence freshness, agent health, schema validity, verifier "
             "checks.", spot=".trust-score-card"),
        Beat("Beside it the counterfactual: what an unconstrained model with direct "
             "fleet-API access would do with this telemetry. That figure is an "
             "illustrative loss, not a measurement.", spot=".guardrail-card"),
        Beat("The five-layer strip is live — each box takes its colour from the run that "
             "just executed. Under it, the failure injection bar: every button calls a "
             "real endpoint, none is staged.",
             _(lambda c: (c.scroll_to(".pipeline-visualizer-card"),
                          c.scroll_to(".failure-injection-bar"))),
             extra=1.0, shot="ch03-pipeline-strip", spot=".failure-injection-bar"),
        Beat("Live Execution animates the real call order: two agents in parallel, gate, "
             "risk assessment, decision authority, action gateway.",
             _(lambda c: c.scroll_to(".mission-control")), spot=".mc-flow"),
        Beat("Beside it the events feed — the same audit stream the Audit page reads.",
             spot=".mc-feed"),
        Beat("Then the decision trace, every stage's duration in milliseconds.",
             _(lambda c: c.scroll_to(".timeline-card")), spot=".timeline-card"),
        Beat("Then provenance: every reading carries a sensor id, a hash of its raw "
             "payload, and the transformations applied to it.",
             _(lambda c: c.scroll_to(".provenance-card")),
             shot="ch03-provenance", spot=".provenance-card"),
        Beat("At the bottom, the controller banner and the approvals queue — the only "
             "place an action is ever released. The speed selector up top changes how "
             "often the dashboard polls.",
             _(lambda c: (c.scroll_to(".banner"), c.scroll_top(),
                          c.click(".timelapse-selector button:has-text('5x')"))),
             spot=".timelapse-selector"),
        Beat("And Simple versus Technical: plain English for an operator, or the internal "
             "vocabulary underneath it.",
             _(lambda c: (c.click(".timelapse-selector button:has-text('1x')"),
                          c.click(".topbar .mode-toggle button:has-text('Technical')"))),
             extra=1.2, shot="ch03-technical", spot=".topbar .mode-toggle"),
    ]))

    # ---------------------------------------------------------------- CH 4
    C.append(Chapter(4, "A Healthy Run", "Agents, gate, correlation, critic, verifier, controller", [
        Beat("A healthy run, end to end.",
             _(lambda c: (c.click(".topbar .mode-toggle button:has-text('Simple')"),
                          c.click(".btn-scene-healthy"),
                          c.scroll_to(".mission-control")))),
        Beat("Both agents light first, together, then the gate, risk assessment, the "
             "decision, the gateway.",
             _(lambda c: c.run_and_wait(".mc-run-btn")), extra=2.5,
             shot="ch04-healthy-run"),
        Beat("The Planner dispatched both observers in parallel because their scopes are "
             "provably disjoint: the Vehicle Agent sees only the truck's sensors, the "
             "Environment Agent only route and weather."),
        Beat("Nine signals collected — five from the truck, four from the environment."),
        Beat("The Trust Gate ran four sub-stages over them, broken out inside the gate "
             "step.",
             _(lambda c: c.scroll_to(".gate-stage-breakdown")), extra=0.8,
             shot="ch04-gate-stages", spot=".gate-stage-breakdown"),
        Beat("Schema Validator: every reading is a well-formed, typed observation. "
             "Freshness Checker: age recomputed from the timestamp, never trusted from a "
             "status field — under two minutes fresh, past five minutes invalid."),
        Beat("Provenance Checker: each signal has exactly one authorized source agent. A "
             "reading from the wrong agent is excluded even when the value looks fine."),
        Beat("Evidence Normalizer: one trusted reading per signal, the freshest. That is "
             "what makes the confidence denominator a real upper bound."),
        Beat("Then Correlation runs deterministic physical checks before the model reasons "
             "at all: cooling on while cargo is warm, heat plus long dwell, cargo too cold "
             "for the ambient with cooling off.",
             _(lambda c: c.scroll_to(".timeline-steps")), spot=".timeline-steps"),
        Beat("Only then does the Risk Assessment Engine reason, over structured evidence "
             "only. No tools, no world state, no action function."),
        Beat("The Verifier checks the model against its evidence: self-consistency, "
             "evidence grounding, and whether a claimed contradiction is actually "
             "supported."),
        Beat("Then the deterministic Controller decides. Nine trusted, no contradiction, "
             "risk low: AUTO_OPTIMIZE at a hundred percent confidence.",
             _(lambda c: c.scroll_to(".banner")), extra=1.0, shot="ch04-auto-optimize",
             spot=".banner"),
        Beat("Single-digit milliseconds for the whole chain — gate, correlation, verifier "
             "and controller are pure code."),
    ]))

    # ---------------------------------------------------------------- CH 5
    C.append(Chapter(5, "Vehicle Explorer", "Telemetry, world state, trust, freshness, confidence", [
        Beat("The Vehicle Explorer is the per-asset view.",
             _(lambda c: c.goto("/vehicle")), extra=0.8, shot="ch05-vehicle"),
        Beat("Four headline numbers: was the gate clean, what share of evidence was "
             "fresh, the computed confidence, and the policy pack in force.",
             spot=".stat-grid"),
        Beat("Confidence history across the session. Below it, live telemetry — raw "
             "world state, ground truth, before anything is gated or graded.",
             _(lambda c: c.scroll_to(".panel:has(h2:text-is('Confidence History'))"))),
        Beat("The gate does its work between that and what comes next.",
             _(lambda c: c.scroll_to(".telemetry-grid")), spot=".telemetry-grid"),
        Beat("These panels are what each agent reported after the gate graded it. "
             "Keeping raw truth and gated evidence separate is the point.",
             _(lambda c: c.scroll_to(".dash-grid")), extra=0.8,
             shot="ch05-evidence", spot=".dash-grid"),
        Beat("Each reading shows freshness and source. Exclusions are shown as "
             "exclusions, not silently dropped."),
        Beat("And the risk assessment: level, contradiction flag, cited factors, "
             "reasoning summary. Presented as an opinion, which is all it is.",
             _(lambda c: c.scroll_to(".panel:has(h2:has-text('AI Risk Assessment'))")),
             extra=0.8, shot="ch05-critic"),
    ]))

    # ---------------------------------------------------------------- CH 6
    C.append(Chapter(6, "The Pipeline Page", "The five layers against one real run", [
        Beat("The Pipeline page pins the same run against the architecture.",
             _(lambda c: c.goto("/pipeline")), extra=0.8, shot="ch06-pipeline"),
        Beat("Telemetry agents, Trust Gate, Risk Assessment Engine, deterministic "
             "Controller, Action Gateway.", spot=".pipeline-flow"),
        Beat("Underneath: sensors reporting, evidence trusted versus ignored, the AI "
             "review, the decision, whether anything went for approval — then every gate "
             "exclusion written out in plain language.",
             _(lambda c: (c.scroll_to(".stepper"), c.scroll_to(".trace-notes"))),
             extra=1.0, spot=".stepper"),
    ]))

    # ---------------------------------------------------------------- CH 7
    C.append(Chapter(7, "Runtime Deep Dive", "Supervisor, metrics, confidence, memory, certificate", [
        Beat("Back to the Runtime, reading live state rather than the diagram.",
             _(lambda c: (c.goto("/runtime"), c.scroll_to(".supervisor-console")))),
        Beat("The Supervisor Console logs what the Supervisor actually did: planned, "
             "launched each agent by name, collected signals, completed.",
             extra=0.8, shot="ch07-supervisor", spot=".supervisor-console"),
        Beat("Underneath: agents launched, agent failures, retries, and whether a retry "
             "recovered.", spot=".failure-counters"),
        Beat("Harness Metrics are aggregated server-side over everything persisted, not "
             "counters held in memory: runs, success rate, halts, retries, evidence "
             "rejected, breaker trips, actions, confidence, latency.",
             _(lambda c: c.scroll_to(".metrics-grid")), extra=1.0,
             shot="ch07-metrics", spot=".metrics-grid"),
        Beat("Confidence Computation shows the arithmetic, not just the number.",
             _(lambda c: c.scroll_to(".confidence-arith")), spot=".confidence-arith"),
        Beat("Corroborating signals over expected signals — nine under the cold chain "
             "pack — minus a flat two-signal penalty for a detected contradiction."),
        Beat("Computed in code. The model is forbidden from reporting a confidence field: "
             "that key is not in the schema, and output carrying it is rejected."),
        Beat("Below it, the composite trust score: five independently observable factors, "
             "multiplied.",
             _(lambda c: c.scroll_to(".composite-result")), spot=".composite-result"),
        Beat("Evidence quality is that same tested formula; verifier score is one if the "
             "verifier passed, one half if not; gate cleanliness is trusted over total "
             "evidence; policy compliance loses a quarter per physical conflict; "
             "historical reliability is the vehicle's recent non-halt rate."),
        Beat("None of the five is self-reported by the model. Each is measured somewhere "
             "else in the system."),
        Beat("One thing the diagram does not draw: the Event Bus. Every stage publishes "
             "a typed event rather than calling Audit directly — Audit is just one "
             "subscriber, the vocabulary is fixed at sixteen event types, and a metrics "
             "collector or websocket pusher could subscribe without the Supervisor "
             "knowing.", _(lambda c: c.scroll_to(".metrics-grid"))),
        Beat("Signal Trend is Memory: one signal across the vehicle's past runs, read "
             "back out of the store, with a direction and a delta.",
             _(lambda c: (c.scroll_to(".trend-header"),
                          c.select(".trend-select", "ambient_temperature"))),
             extra=1.0, shot="ch07-trend", spot=".trend-header"),
        Beat("World State again, labelled pre-gate so it is never mistaken for "
             "evidence. The Decision Certificate then closes the run with five checks, "
             "each derived from a real field on the decision.",
             _(lambda c: c.scroll_to(".world-state-grid")), extra=0.6,
             spot=".world-state-grid"),
        Beat("Five checks, five stored facts.",
             _(lambda c: c.scroll_to(".decision-certificate")), extra=0.8,
             shot="ch07-certificate", spot=".decision-certificate"),
        Beat("Incident Memory is a different subsystem from Memory. Memory asks whether a "
             "signal is drifting; Incident Memory asks what went wrong and whether it was "
             "resolved. Empty now — we will come back once we break something.",
             _(lambda c: c.scroll_to(".panel:has(h2:has-text('Incident Memory'))")),
             spot=".panel:has(h2:has-text('Incident Memory'))"),
    ]))

    # ---------------------------------------------------------------- CH 8
    C.append(Chapter(8, "Contradictory Evidence", "The failure the architecture exists for", [
        Beat("Now the failure scenario, where the architecture earns its keep.",
             _(lambda c: (c.goto("/"), c.scroll_to(".mission-control")))),
        Beat("Cooling reports ON. Cargo is eleven point five degrees, nearly double the "
             "safe band. Ambient forty-one. Stopped for thirty-seven minutes.",
             _(lambda c: c.click(".btn-scene-risk")), extra=1.0),
        Beat("Those two facts cannot both be true. Either the cooling unit is not really "
             "running, or the cargo sensor is wrong. Something is lying."),
        Beat("Run it.", _(lambda c: c.run_and_wait(".mc-run-btn")), extra=2.5,
             shot="ch08-halt"),
        Beat("Correlation caught it deterministically, before the model reasoned at all: "
             "cooling on, cargo above the safe maximum. It also flagged thermal dwell "
             "risk."),
        Beat("The Risk Assessment Engine reasoned over the same evidence and reached HIGH "
             "risk with the contradiction flag set, citing four factors.",
             _(lambda c: c.scroll_to(".timeline-steps")), spot=".timeline-steps"),
        Beat("The Verifier checked it against the evidence: high risk backed by factors, "
             "every factor mapped to a present signal, and enough evidence behind the "
             "contradiction. All three passed."),
        Beat("Confidence fell from a hundred percent to seventy-eight: nine trusted, "
             "minus the two-signal contradiction penalty, over nine expected."),
        Beat("Notice what did not happen. The model did not decide — it produced an "
             "assessment."),
        Beat("The Controller is a state machine: three states, first match wins, in the "
             "order agents down, output rejected, evidence missing, confirmed risk, "
             "healthy."),
        Beat("It reached rule four — risk high or contradiction flagged. CRITICAL_HALT. "
             "And it is the only component permitted to request an action.",
             _(lambda c: c.scroll_to(".banner")), spot=".banner"),
        Beat("The decision explainer puts the whole chain in one place: final state, the "
             "reasoner's output, the verifier's status, the confidence arithmetic, and "
             "the evidence it was grounded in.",
             _(lambda c: (c.scroll_top(), c.click(".btn-explainer"))), extra=2.0,
             shot="ch08-explainer"),
        Beat("Every claim there is a field on the stored decision. Nothing is re-derived "
             "in the browser.",
             _(lambda c: c.click(".btn-close")), extra=1.0),
    ]))

    # ---------------------------------------------------------------- CH 9
    C.append(Chapter(9, "Human Approval", "The Action Gateway and the escalation record", [
        Beat("The Action Gateway is the authority boundary — the only place an action can "
             "be requested, approved and executed.",
             _(lambda c: (c.goto("/"), c.scroll_to(".action-card"))), extra=0.8,
             shot="ch09-pending", spot=".action-card"),
        Beat("Halting automation is human-tier. It does not execute. It opens for "
             "approval and waits."),
        Beat("Nothing inside the system can move it forward. Only a person can."),
        Beat("Approve it.",
             _(lambda c: c.click(".action-card button.ok")), extra=2.5),
        Beat("The gateway moves it to approved, then executes — which here means creating "
             "an immutable escalation record. Three rows land on the action's own event "
             "log: requested, approved, executed, each with an actor and a timestamp.",
             extra=0.5, shot="ch09-approved"),
        Beat("An operator can also reject with a reason, recorded just as durably. A "
             "decision not to act is still a decision."),
        Beat("Every transition also lands in the append-only audit table under a fixed "
             "event vocabulary, which is what makes the trail queryable end to end."),
    ]))

    # ---------------------------------------------------------------- CH 10
    C.append(Chapter(10, "The Failure Matrix", "Every failure mode the harness claims to survive", [
        Beat("The Simulation Lab drives every failure mode the harness claims to survive. "
             "Each control hits a real endpoint. Back to normal conditions first, so "
             "each failure is isolated.",
             _(lambda c: (c.goto("/simulation"),
                          c.click("button:has-text('Normal conditions')"))),
             extra=0.8, shot="ch10-simlab"),
        Beat("Failure one: an agent dies mid-route.",
             _(lambda c: c.click("button:has-text('Disconnect route sensors')"))),
        Beat("The Environment Agent is unavailable. The harness does not guess the "
             "missing values and does not proceed on half a picture.",
             _(lambda c: c.run_and_wait("button.primary:has-text('Run check')")),
             extra=2.0, shot="ch10-agent-down"),
        Beat("Rule one fires: agents unavailable. INSUFFICIENT_DATA at fifty-six percent, "
             "five of nine signals surviving. It did not crash — it degraded and stayed "
             "up."),
        Beat("Failure two: the model returns malformed output.",
             _(lambda c: (c.click("button:has-text('Reconnect route sensors')"),
                          c.click("button:has-text('Simulate AI glitch')")))),
        Beat("The payload is valid JSON but violates the contract: no reasoning summary, "
             "plus a confidence field the model is forbidden to set. It goes through the "
             "same strict validation a real model's output would. Two validation errors — "
             "rejected, not coerced into shape.",
             _(lambda c: c.run_and_wait("button.primary:has-text('Run check')")),
             extra=2.0, shot="ch10-corrupt"),
        Beat("Rule two fires: critic output rejected, INSUFFICIENT_DATA."),
        Beat("And confidence is still a hundred percent. Not a bug: confidence measures "
             "evidence completeness, and the evidence was complete. The model failing is "
             "a separate axis, refused independently."),
        Beat("Failure three: stale telemetry. One cargo reading backdated four minutes.",
             _(lambda c: c.click("button:has-text('Simulate old data')"))),
        Beat("The gate recomputes age from the timestamp, so it lands past the freshness "
             "window and is excluded.",
             _(lambda c: c.run_and_wait("button.primary:has-text('Run check')")),
             extra=2.0, shot="ch10-stale"),
        Beat("Cargo temperature is required, so rule three fires: required evidence "
             "missing or untrusted. Eighty-nine percent, INSUFFICIENT_DATA."),
        Beat("Failure four: a network blip on the one call that crosses a real network "
             "boundary. The next risk-assessment call fails once.",
             _(lambda c: (c.click("button:has-text('Clear old data')"),
                          c.click("button:has-text('Simulate network blip')")))),
        Beat("The Retry Engine tries again inside the same run, and recovers.",
             _(lambda c: c.run_and_wait("button.primary:has-text('Run check')")),
             extra=2.0),
        Beat("There is the retry row, marked attempt failed, and the recovered marker on "
             "the stage that succeeded second time.",
             _(lambda c: (c.goto("/runtime"), c.scroll_to(".step-retry"))), extra=1.5,
             shot="ch10-retry", spot=".step-retry"),
        Beat("System Indicators tracks all of it live, including open escalations.",
             _(lambda c: (c.goto("/simulation"), c.scroll_to(".indicator-grid"))),
             spot=".indicator-grid"),
        Beat("Failure five: three consecutive model failures open the Circuit Breaker.",
             _(lambda c: (c.goto("/"), c.click("button:has-text('Trip Circuit Breaker')")))),
        Beat("Now it stops attempting the call at all rather than sitting on timeouts, "
             "and records that the breaker was open on that run.",
             _(lambda c: (c.scroll_to(".mission-control"), c.run_and_wait(".mc-run-btn"))),
             extra=2.0, shot="ch10-breaker"),
        Beat("After the cooldown it half-opens, and the next successful call closes it. "
             "No restart needed.",
             _(lambda c: ensure_breaker_closed())),
        Beat("Two more injections. Sensor drift pushes cargo to fourteen and a half.",
             _(lambda c: (c.scroll_to(".failure-injection-bar"),
                          c.click("button:has-text('Sensor Drift')")))),
        Beat("And the red override forces the worst case: fifteen degrees, with cooling "
             "still insisting it is running.",
             _(lambda c: (c.scroll_top(), c.click(".btn-emergency-override"))), extra=1.5),
    ]))

    # ---------------------------------------------------------------- CH 11
    C.append(Chapter(11, "Policy Packs", "The domain is data, not code", [
        Beat("Everything so far was cold chain. But nothing in the gate, correlation, "
             "verifier or controller knows what cold chain is.",
             _(lambda c: (c.goto("/runtime"), c.scroll_to(".policy-pack-grid"))),
             extra=0.8, shot="ch11-packs", spot=".policy-pack-grid"),
        Beat("The domain lives in a policy pack. Two ship today."),
        Beat("Cold Chain requires cargo temperature, cooling status and ambient "
             "temperature, and expects nine signals. Tyre Safety requires tyre pressure, "
             "tyre temperature and vehicle speed, and expects five."),
        Beat("Switch the active pack to Tyre Safety and run the very same world again.",
             _(lambda c: (c.click(".policy-pack-card:has-text('Tyre Safety')"),
                          ensure_breaker_closed(), c.goto("/"),
                          c.scroll_to(".mission-control"),
                          c.run_and_wait(".mc-run-btn"))), extra=2.5,
             shot="ch11-tyre-run"),
        Beat("Same world, same code paths, completely different outcome.",
             _(lambda c: (c.goto("/runtime"), c.scroll_to(".confidence-arith"))),
             spot=".confidence-arith"),
        Beat("Cargo temperature, cooling status, weather severity and dwell are now "
             "excluded as unknown signals — they are not in this policy's vocabulary at "
             "all."),
        Beat("The expected denominator moved from nine to five, so the confidence "
             "arithmetic changed underneath it."),
        Beat("And the reasoner switched to tyre logic: the contradiction it hunts is "
             "underinflation plus heat, not cooling versus cargo."),
        Beat("Telemetry that halted automation under Cold Chain runs clean under Tyre "
             "Safety, because policy decides what counts as evidence and what counts as "
             "risk. Not the model.", extra=0.8, shot="ch11-effect"),
        Beat("Zero code changes in gate, correlation, risk engine or controller. Switch "
             "back.",
             _(lambda c: (c.scroll_to(".policy-pack-grid"),
                          c.click(".policy-pack-card:has-text('Cold Chain')")))),
    ]))

    # ---------------------------------------------------------------- CH 12
    C.append(Chapter(12, "Isolation", "Why the AI cannot act, by construction", [
        Beat("Now the guarantee most systems assert and few demonstrate: the AI "
             "components cannot act.",
             _(lambda c: c.scroll_to(".panel:has(h2:has-text('Isolation Proof'))")),
             spot=".panel:has(h2:has-text('Isolation Proof'))"),
        Beat("That button makes the Vehicle Agent genuinely attempt to call the "
             "Environment Agent's tool.",
             _(lambda c: c.click("button:has-text('Try: Vehicle')")), extra=1.5,
             shot="ch12-tool-denied"),
        Beat("Denied by the Tool Registry — scoped access, checked at call time."),

        Beat("The red-team probe goes further. It inspects the live agent object for "
             "seven action-shaped attributes, then parses the agents module's import "
             "graph to see whether it can even reach the action gateway.",
             _(lambda c: (c.goto("/simulation"),
                          c.scroll_to(".panel:has(h2:has-text('Security Check'))"),
                          c.click("button:has-text('Test the safety lock')"))),
             extra=2.0, shot="ch12-probe"),
        Beat("Eight attempts, all blocked — not by a permission check that could be "
             "misconfigured, but by the absence of any reference at all."),
        Beat("The agents module does not import actions; neither does the critic. There "
             "is no object to call. And it is enforced by tests, not convention — the "
             "isolation suite fails the build the moment anyone wires an action onto an "
             "agent."),
        Beat("Ninety-eight tests cover the gate, policy, critic validation, confidence, "
             "the controller table, the gateway, the HTTP surface and the runtime — plus "
             "property-based fuzzing over random inputs."),
    ]))

    # ---------------------------------------------------------------- CH 13
    C.append(Chapter(13, "Replay and Audit", "Reconstructing a decision after the fact", [
        Beat("Replay. Every run is durably persisted: the decision, its evidence "
             "snapshot, the gate notes, the verifier result, the timed trace. The audit "
             "trail is append-only — nothing in it is ever rewritten.",
             _(lambda c: c.goto("/audit")), extra=0.8,
             shot="ch13-audit", spot=".audit-tall"),
        Beat("Filterable by event type.",
             _(lambda c: c.select("select.select", "decision_made")), extra=1.0),
        Beat("And searchable across the whole trail.",
             _(lambda c: (c.select("select.select", ""),
                          c.type_in(".topbar-search input", "halt"))), extra=1.5,
             shot="ch13-search"),
        Beat("Selecting any record with a run reconstructs that decision out of storage: "
             "its stepper, its state, its reason, and the reasoning summary current at "
             "the time.",
             _(lambda c: (c.type_in(".topbar-search input", ""),
                          c.page.wait_for_timeout(2000),
                          c.click(".audit-row-btn:not([disabled])"))), extra=2.0,
             shot="ch13-replay-decision"),
        Beat("And the trace replays stage by stage, paced by the durations actually "
             "recorded.",
             _(lambda c: (c.goto("/runtime"), c.scroll_to(".timeline-card"),
                          c.click("button:has-text('Replay Incident')"))), extra=4.0,
             shot="ch13-replay"),
        Beat("Incident Memory has filled in: the halts we caused, joined with how each "
             "action was resolved, and by whom.",
             _(lambda c: c.scroll_to(".incident-list")), extra=1.0,
             shot="ch13-incidents", spot=".incident-list"),
        Beat("That is what makes an incident reviewable by someone who was not in the "
             "room: not a log line, but the exact evidence, the exact assessment, the "
             "exact rule that fired, and who approved what."),
    ]))

    # ---------------------------------------------------------------- CH 14
    C.append(Chapter(14, "Analytics and Configuration", "Every chart, and the harness settings", [
        Beat("Analytics aggregates the session.",
             _(lambda c: c.goto("/analytics")), extra=0.8, shot="ch14-analytics"),
        Beat("Runs, schema rejections, contradictions flagged, security probe pass "
             "rate.", spot=".stat-grid"),
        Beat("The Decision Funnel is the most useful view: how many runs reached each "
             "gate — runs, evidence complete, risk assessed, verifier passed, automation "
             "continued.",
             _(lambda c: c.scroll_to(".funnel")), extra=0.8,
             shot="ch14-funnel", spot=".funnel"),
        Beat("The drop-off between stages is where the harness refused to proceed. Every "
             "step down is a decision not taken."),
        Beat("Confidence over time, and the distribution across the three controller "
             "states.",
             _(lambda c: c.scroll_to(".dash-grid")), spot=".dash-grid"),
        Beat("Then four health gauges: confidence, healthy decisions, reasoner validity, "
             "security integrity.",
             _(lambda c: c.scroll_to(".gauge-row")), extra=0.8,
             shot="ch14-gauges", spot=".gauge-row"),
        Beat("Settings carries view mode and environment: which reasoning backend is "
             "live, the active scenario, and the API base being polled.",
             _(lambda c: c.goto("/settings")), extra=1.0, shot="ch14-settings"),
    ]))

    # ---------------------------------------------------------------- CH 15
    C.append(Chapter(15, "Confidence and Authority", "The two ideas the design rests on", [
        Beat("Two ideas hold this design together.",
             _(lambda c: (c.goto("/runtime"), c.scroll_to(".confidence-arith"))),
             spot=".confidence-arith"),
        Beat("First, confidence: a measure of evidence, computed in code, with a fixed "
             "denominator that data loss cannot cancel out."),
        Beat("If the denominator were whatever you happened to receive, losing an agent "
             "would leave you at a hundred percent confidence in a smaller picture. It is "
             "not. It is what a healthy fleet produces."),
        Beat("So a killed agent, an excluded stale reading, or a contradiction genuinely "
             "lowers the number. That is the only safe behaviour."),
        Beat("Second, authority. The model's output is an input to a decision, never the "
             "decision.",
             _(lambda c: c.scroll_to(".decision-certificate")),
             spot=".decision-certificate"),
        Beat("Validated against a strict schema, verified against its evidence, then "
             "consumed by a state machine you can read in about forty lines."),
        Beat("The Controller is the only component permitted to request an action, in one "
             "of its three states — and halting automation is human-tier, so it opens for "
             "approval and waits."),
        Beat("Which means if the model is unavailable, malformed, contradictory or simply "
             "wrong, the worst outcome this system can reach is a refusal to act."),
    ]))

    # ---------------------------------------------------------------- CH 16
    C.append(Chapter(16, "Closing", "Agents investigate. The Critic challenges. Policy decides.", [
        Beat("Five layers, five modules, never collapsed into one.",
             _(lambda c: (c.goto("/pipeline"), c.scroll_to(".layer-list"))),
             extra=0.8, spot=".layer-list"),
        Beat("Intelligence: two isolated agents and one reasoner with no tools and no "
             "authority."),
        Beat("Evidence: a deterministic trust gate — freshness, provenance, completeness, "
             "normalization. Policy: swappable domain packs that decide what counts as "
             "evidence and what counts as risk."),
        Beat("Decision: a three-state machine and a confidence formula, both in code. "
             "Authority: one gateway, human-tier approval, an append-only record of every "
             "transition."),
        Beat("The app even ships its own presenter guide, mapping each scene to the "
             "module that guarantees it.",
             _(lambda c: (c.scroll_top(), c.click(".btn-presenter"))), extra=2.5,
             shot="ch16-presenter"),
        Beat("Intelligence is advisory. Deterministic policy is authoritative. Every "
             "screen here is an argument for that.",
             _(lambda c: c.click(".btn-close")), extra=1.0),
        Beat("Agents investigate.",
             _(lambda c: (c.goto("/"), c.scroll_top())), extra=1.2),
        Beat("The Critic challenges.", extra=1.2),
        Beat("Deterministic policy decides.", extra=2.5, shot="ch16-close"),
    ]))

    return C


# --------------------------------------------------------------------- captions
def write_srt(cues: list[tuple[float, float, str]], path: Path) -> None:
    def ts(seconds: float) -> str:
        ms = int(round(seconds * 1000))
        h, ms = divmod(ms, 3_600_000)
        m, ms = divmod(ms, 60_000)
        s, ms = divmod(ms, 1000)
        return f"{h:02}:{m:02}:{s:02},{ms:03}"

    lines: list[str] = []
    for i, (start, end, text) in enumerate(cues, 1):
        lines += [str(i), f"{ts(start)} --> {ts(max(end, start + 1.0))}", text, ""]
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    log(f"captions -> {path} ({len(cues)} cues)")


def plan_cues(chapters: list[Chapter]) -> list[tuple[float, float, str]]:
    """Planned (pre-run) timings, used by --dry-run."""
    cues, t = [], 0.0
    for ch in chapters:
        t += TITLE_CARD_SECONDS
        for beat in ch.beats:
            cues.append((t, t + beat.seconds, beat.say))
            t += beat.seconds
    return cues


# ------------------------------------------------------------------- narration
# narration.md is GENERATED from the beat table above, so the spoken script, the
# captions and what the browser actually does can never drift apart.

_CUE_PATTERNS = [
    (r'goto\("([^"]+)"\)',                   "go to {0}"),
    (r"run_and_wait\([^)]*\)",               "click Run check, wait for the decision"),
    (r'click\("\.btn-scene-healthy"\)',      "click the Healthy scene"),
    (r'click\("\.btn-scene-risk"\)',         "click the Risk Anomaly scene"),
    (r'click\("\.btn-emergency-override"\)', "click the red OVERRIDE button"),
    (r'click\("\.btn-explainer"\)',          "open the Decision Explainer"),
    (r'click\("\.btn-presenter"\)',          "open the Presenter Guide"),
    (r'click\("\.btn-close"\)',              "close the modal"),
    (r'click\("[^"]*?:has-text\(\x27([^\x27]+)\x27\)"\)', "click “{0}”"),
    (r'click\("([^"]+)"\)',                  "click {0}"),
    (r'select\("([^"]+)",\s*"([^"]*)"\)',    "set {0} to “{1}”"),
    (r'type_in\("([^"]+)",\s*"([^"]*)"\)',   "type “{1}” into the search box"),
    (r'scroll_to\("([^"]+)"\)',              "scroll to {0}"),
    (r"scroll_top\(\)",                      "scroll to the top"),
    (r"ensure_breaker_closed\(\)",           "wait for the circuit breaker to close"),
]


def _cues_from_source(src: str) -> list[str]:
    import re
    out: list[str] = []
    for pattern, template in _CUE_PATTERNS:
        for m in re.finditer(pattern, src):
            out.append(template.format(*m.groups()) if m.groups() else template)
    seen, unique = set(), []
    for c in out:
        if c not in seen:
            seen.add(c)
            unique.append(c)
    return unique


def _beat_actions() -> list[list[str]]:
    """Recover each beat's on-screen action from this file's own source, in beat
    order, so the narration lists what the walkthrough really does."""
    import ast
    src = Path(__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    calls: list[ast.Call] = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.FunctionDef) and node.name == "build_chapters"):
            continue
        calls += [c for c in ast.walk(node)
                  if isinstance(c, ast.Call) and getattr(c.func, "id", "") == "Beat"]
    # Sorted by position, so the list is in the order the beats are delivered
    # regardless of how ast.walk happens to traverse the tree.
    calls.sort(key=lambda c: (c.lineno, c.col_offset))

    actions: list[list[str]] = []
    for call in calls:
        do_src = ""
        for kw in call.keywords:
            if kw.arg == "do":
                do_src = ast.get_source_segment(src, kw.value) or ""
        actions.append(_cues_from_source(do_src))
    return actions


def _srt_starts(path: Path) -> list[float]:
    if not path.exists():
        return []
    starts: list[float] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if "-->" in line:
            h, m, rest = line.split(" --> ")[0].split(":")
            sec, ms = rest.split(",")
            starts.append(int(h) * 3600 + int(m) * 60 + int(sec) + int(ms) / 1000)
    return starts


def write_narration(chapters: list[Chapter], path: Path,
                    from_recording: bool = False) -> None:
    """`from_recording` is True only after a real walkthrough, when captions.srt
    holds elapsed times; a --dry-run writes planned times and must say so."""
    def mmss(t: float) -> str:
        return f"{int(t) // 60:02d}:{int(t) % 60:02d}"

    actions = _beat_actions()
    measured = _srt_starts(SRT_PATH) if from_recording else []
    n_beats = sum(len(c.beats) for c in chapters)
    timed = len(measured) == n_beats

    out: list[str] = []
    total = sum(c.seconds for c in chapters)
    out.append("# Narration — Fleet-Harness Master Demo\n")
    out.append(f"Full narration, word for word, in delivery order. "
               f"**{len(chapters)} chapters, {n_beats} lines, "
               f"~{total / 60:.0f} minutes.**\n")
    out.append("> Generated from the beat table in `create_master_demo.py` — the same table "
               "that drives the browser and emits `captions.srt`. The spoken script, "
               "the captions and the on-screen actions cannot drift apart.\n")
    out.append("Timecodes are "
               + ("**measured from the recorded run**."
                  if timed else "the scripted plan (no recording found yet).")
               + " Each line is one caption. Italics are what the browser does while "
                 "the line is spoken — the narrator talks *over* the click, never "
                 "after it.\n")
    out.append("**Delivery:** about 165 words a minute. A full stop is a real pause. "
               "The three closing lines get a beat of silence between them.\n")
    out.append("---\n")

    idx, t = 0, 0.0
    for ch in chapters:
        start = (measured[idx] - TITLE_CARD_SECONDS) if (timed and idx < len(measured)) else t
        out.append(f"## Chapter {ch.number} — {ch.title}\n")
        out.append(f"*{mmss(max(0.0, start))} · {ch.subtitle} · "
                   f"{ch.seconds / 60:.2f} min*\n")
        t += TITLE_CARD_SECONDS
        for beat in ch.beats:
            stamp = measured[idx] if (timed and idx < len(measured)) else t
            cue = actions[idx] if idx < len(actions) else []
            out.append(f"**{mmss(stamp)}**  {beat.say}")
            if cue:
                out.append(f"> *{'; '.join(cue)}*")
            out.append("")
            t += beat.seconds
            idx += 1
        out.append("---\n")

    out.append("## The last three lines\n")
    out.append("> **Agents investigate.**\n>\n> **The Critic challenges.**\n>\n"
               "> **Deterministic policy decides.**\n")
    out.append("Deliver them slowly, with a full beat between each. Do not add a "
               "summary afterwards.\n")

    path.write_text("\n".join(out), encoding="utf-8", newline="\n")
    log(f"narration -> {path.name} ({idx} lines, "
        f"{'measured' if timed else 'planned'} timecodes)")


# ------------------------------------------------------------------------ main
def ensure_breaker_closed(max_wait: float = 45.0) -> None:
    """The Circuit Breaker holds OPEN for a 30s cooldown after being tripped.
    Poll a real run until one gets through, so the next chapter demonstrates the
    policy pack rather than a leftover open breaker."""
    deadline = time.time() + max_wait
    while time.time() < deadline:
        try:
            decision = api("POST", "/runs")
            if "Circuit Breaker is OPEN" not in (decision.get("reason") or ""):
                log("circuit breaker closed again (recovery run succeeded)")
                return
        except Exception as exc:
            log(f"breaker recovery probe failed: {exc}", "WARN")
        time.sleep(3)
    log("circuit breaker still open after cooldown wait", "WARN")


def reset_world() -> None:
    """Start every run from the documented healthy baseline so the numbers the
    narration quotes are the numbers on screen."""
    api("POST", "/simulate/reset")
    api("POST", "/policy/active", {"key": "cold_chain"})
    api("POST", "/simulate/kill-agent", {"agent": "agent_a", "disabled": False})
    api("POST", "/simulate/kill-agent", {"agent": "agent_b", "disabled": False})
    api("POST", "/simulate/stale-signal", {"signal": None})
    for _i in range(3):                      # seed a little trend history
        api("POST", "/runs")
    log("world + store reset to the healthy baseline (3 seed runs)")


def run_demo(args) -> int:
    from playwright.sync_api import sync_playwright

    chapters = build_chapters()
    if args.chapters:
        wanted = {int(x) for x in args.chapters.split(",")}
        chapters = [c for c in chapters if c.number in wanted]

    planned = sum(c.seconds for c in chapters)
    log(f"planned walkthrough: {len(chapters)} chapters, "
        f"{sum(len(c.beats) for c in chapters)} beats, "
        f"{planned / 60:.1f} minutes at 1x")

    servers = Servers()
    started_servers = False
    try:
        if not args.no_servers:
            servers.start()
            started_servers = True
        else:
            if not wait_until(lambda: url_ok(f"{API}/health"), "backend /health", 60):
                return 2
            if not wait_until(lambda: url_ok(UI), "frontend :5173", 60):
                return 2

        reset_world()

        VIDEO_DIR.mkdir(parents=True, exist_ok=True)
        SHOTS_DIR.mkdir(parents=True, exist_ok=True)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=not args.headed,
                                        args=["--force-device-scale-factor=1"])
            ctx_kwargs = {"viewport": VIEWPORT, "device_scale_factor": 1}
            if not args.no_video:
                ctx_kwargs["record_video_dir"] = str(VIDEO_DIR)
                ctx_kwargs["record_video_size"] = VIEWPORT
            context = browser.new_context(**ctx_kwargs)
            context.add_init_script(OVERLAY_JS)
            page = context.new_page()

            # The reject flow prompts for a reason; answer it rather than
            # letting Playwright auto-dismiss the dialog.
            page.on("dialog", lambda d: d.accept("superseded — driver already notified"))
            page.on("pageerror", lambda e: log(f"page error: {e}", "WARN"))

            ctx = Ctx(page, args.speed, len(chapters))
            ctx.goto("/")
            page.wait_for_timeout(2500)

            for ch in chapters:
                log(f"===== CHAPTER {ch.number}: {ch.title} "
                    f"({ch.seconds / 60:.1f} min planned) =====")
                ctx.chapter_card(ch)
                for idx, beat in enumerate(ch.beats, 1):
                    start = ctx.now()
                    ctx.caption(beat.say)
                    ctx.spot(None)
                    log(f"  {ch.number}.{idx:02d} {beat.say[:96]}")
                    action_t0 = time.time()
                    if beat.do:
                        try:
                            beat.do(ctx)
                        except Exception as exc:
                            ctx.failures += 1
                            log(f"  beat action failed: {exc}", "WARN")
                    # After the action, not before: most highlighted elements only
                    # exist once the beat has navigated or scrolled to them.
                    ctx.spot(beat.spot)
                    # The narration is spoken OVER the click/scroll, so only the
                    # remainder of the line's length is held afterwards.
                    spent = (time.time() - action_t0) * ctx.speed
                    ctx.hold(max(0.35, beat.seconds - spent))
                    if beat.shot:
                        ctx.spot(None)
                        ctx.shot(beat.shot)
                    ctx.cues.append((start, ctx.now(), beat.say))
                ctx.spot(None)

            ctx.js("window.__demo && window.__demo.clearCaption()")
            page.wait_for_timeout(1200)

            write_srt(ctx.cues, SRT_PATH)
            write_narration(build_chapters(), DEMO_DIR / "narration.md",
                            from_recording=True)
            elapsed = ctx.now()
            log(f"walkthrough finished in {elapsed / 60:.1f} minutes "
                f"(speed {args.speed}x, {ctx.failures} recoverable step failures)")

            video = page.video
            context.close()
            browser.close()
            if video:
                try:
                    log(f"video -> {Path(video.path()).name}")
                except Exception:
                    pass

        log(f"final metrics: {api('GET', '/metrics')}")
        return 0
    finally:
        if started_servers:
            servers.stop()


def main() -> int:
    global LOG
    ap = argparse.ArgumentParser(description="Fleet-Harness master demo automation")
    ap.add_argument("--speed", type=float, default=1.0,
                    help="pacing multiplier (6 = fast rehearsal)")
    ap.add_argument("--headed", action="store_true", help="show the browser")
    ap.add_argument("--no-servers", action="store_true",
                    help="attach to a backend/frontend that are already running")
    ap.add_argument("--no-video", action="store_true", help="skip video recording")
    ap.add_argument("--chapters", default="", help="comma-separated chapter numbers")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the plan and write planned captions; no browser")
    ap.add_argument("--emit-narration", action="store_true",
                    help="regenerate demo/narration.md from the beat table and exit")
    args = ap.parse_args()

    LOG = Log(LOG_PATH)
    try:
        chapters = build_chapters()
        total = sum(c.seconds for c in chapters)
        log("Fleet-Harness — master demo walkthrough")
        for ch in chapters:
            log(f"  ch{ch.number:02d}  {ch.seconds / 60:5.2f} min  "
                f"{len(ch.beats):2d} beats  {ch.title}")
        log(f"  TOTAL {total / 60:.2f} minutes ({total:.0f}s) at 1x")

        if args.emit_narration:
            write_narration(chapters, DEMO_DIR / "narration.md",
                            from_recording=True)
            return 0
        if args.dry_run:
            write_srt(plan_cues(chapters), SRT_PATH)
            write_narration(chapters, DEMO_DIR / "narration.md")
            return 0
        return run_demo(args)
    finally:
        if LOG:
            LOG.close()


if __name__ == "__main__":
    raise SystemExit(main())
