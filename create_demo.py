#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fleet-Harness — fully automated 3-minute hackathon demo video.

    python create_demo.py   ->   demo/ColdChain-Harness-Demo.mp4

No manual screen recording, no manual clicking, no mock UI. The pipeline:

  1. NARRATE   Synthesise every narration line to WAV (Windows SAPI, offline) and
               measure each clip. Narration length is what paces the whole video,
               so the capture is pause-free by construction rather than having
               dead air cut out afterwards.
  2. SERVE     Start the real FastAPI backend and the real Vite frontend, wait
               for both to be ready, reset the world to the documented baseline.
  3. CAPTURE   Drive the real UI with Playwright at 1920x1080 while recording.
               Every scenario is triggered through the same control an operator
               would click; every number on screen comes from the running system.
  4. ASSEMBLE  ffmpeg: render title/end cards, trim the three acts out of the
               capture, cross-fade them together, mix the narration onto the
               timeline, burn in captions, encode H.264 + AAC.

ffmpeg comes from `imageio-ffmpeg` (a pip wheel with a bundled binary) if it is
not already on PATH; the script installs it on demand.

Flags:
    --no-servers      attach to a backend/frontend already running
    --skip-capture    reuse the previous capture, re-assemble only
    --skip-tts        reuse previously synthesised narration
    --headed          watch the browser drive
    --keep-build      keep the intermediate build/ artifacts
    --dry-run         print the beat plan and narration word counts, then exit
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
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parent
BACKEND_DIR = ROOT / "backend"
FRONTEND_DIR = ROOT / "frontend"
DEMO_DIR = ROOT / "demo"
BUILD_DIR = DEMO_DIR / "build"
AUDIO_DIR = BUILD_DIR / "audio"
CAPTURE_DIR = BUILD_DIR / "capture"

OUTPUT = DEMO_DIR / "ColdChain-Harness-Demo.mp4"
LOG_PATH = DEMO_DIR / "video_pipeline.log"

API = "http://localhost:8000"
UI = "http://localhost:5173"

W, H, FPS = 1920, 1080, 30
XFADE = 0.6           # seconds of cross-fade between acts
BEAT_GAP = 0.30       # breath between narration lines
VOICE = "Microsoft David Desktop"
VOICE_RATE = 2        # SAPI -10..10; 2 measures at ~176 wpm

# This ffmpeg build has libfreetype and libass but no usable fontconfig on
# Windows: drawtext silently falls back to a serif face, and libass cannot
# resolve a font by name. Both filters are therefore pointed at real files.
FONT_CANDIDATES = [
    ("C:/Windows/Fonts/segoeuib.ttf", "C:/Windows/Fonts/segoeui.ttf", "Segoe UI"),
    ("C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/arial.ttf", "Arial"),
    ("C:/Windows/Fonts/calibrib.ttf", "C:/Windows/Fonts/calibri.ttf", "Calibri"),
]
FONT_BOLD = FONT_REGULAR = ""
FONT_NAME = "Segoe UI"

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


# ------------------------------------------------------------------------ log
class Log:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.fh = path.open("w", encoding="utf-8", newline="\n")
        self.t0 = time.time()

    def __call__(self, msg: str, level: str = "INFO") -> None:
        line = f"[{time.time() - self.t0:7.2f}s] {level:5} {msg}"
        print(line, flush=True)
        self.fh.write(line + "\n")
        self.fh.flush()

    def close(self) -> None:
        self.fh.close()


LOG: "Log | None" = None


def log(msg: str, level: str = "INFO") -> None:
    (LOG or print)(msg, level) if LOG else print(msg, flush=True)


# =============================================================== THE BEAT TABLE
# Each beat is one narration line plus what the browser does while it is spoken.
# Every claim here was checked against the running system; nothing is staged.

@dataclass
class Beat:
    key: str
    say: str
    do: "Callable[[Ctx], None] | None" = None
    pad: float = 0.0            # extra seconds after the line (let a UI settle)
    caption: str | None = None  # defaults to `say`

    # filled in by the pipeline
    audio: Path | None = None
    audio_secs: float = 0.0
    t_start: float = 0.0        # wall clock, set during capture
    t_end: float = 0.0


@dataclass
class Act:
    key: str
    title: str
    beats: list[Beat] = field(default_factory=list)
    t_start: float = 0.0
    t_end: float = 0.0


def build_acts() -> list[Act]:
    """Fleet-Harness hackathon pitch — Script B (submission cut), rebuilt
    against the redesigned frontend: the old scene-preset buttons are gone,
    replaced by the Shipment Evaluation form (a "Scenario" dropdown + real
    telemetry fields, submitting POST /simulate/shipment then POST /runs in
    one click) and the new 8-stage Live Runtime Pipeline visualization. Every
    click hits a real endpoint on the real running app — nothing is staged,
    including the Verifier -> Risk Assessment Engine feedback loop, which is
    genuinely armed via /simulate/verifier-feedback before that run executes."""
    A: list[Act] = []

    SCENARIO_SELECT = ".shipment-form-grid label.field:has-text('Scenario') select"
    POLICY_SELECT = ".shipment-form-grid label.field:has-text('Policy Pack') select"
    EVALUATE_BTN = ".btn-evaluate"

    # The wrapping <label> (not the bare <select>/<input>), so the spotlight
    # ring includes the field's caption — a judge sees "Scenario" or "Policy
    # Pack" highlighted, not just an unlabelled box. Used to ring the exact
    # field a line of narration is talking about, instead of only ringing the
    # result cards after the fact.
    SCENARIO_FIELD = ".shipment-form-grid label.field:has-text('Scenario')"
    POLICY_FIELD = ".shipment-form-grid label.field:has-text('Policy Pack')"
    COOLING_FIELD = ".shipment-form-grid label.field:has-text('Cooling Status')"
    CARGO_FIELD = ".shipment-form-grid label.field:has-text('Cargo Temperature')"

    # ------------------------------------------------------------- ACT 1
    A.append(Act("act1", "The problem, the harness, and a healthy run", [
        Beat("b01",
             "When AI makes operational decisions, intelligence isn't the hard "
             "part — trust is. Cargo here spoils outside two to six degrees.",
             lambda c: c.goto("/")),
        Beat("b02",
             "A model deciding alone fails three ways: bad data trusted, bad "
             "reasoning trusted, authority handed away.",
             None),
        Beat("b03",
             "So: a harness, not an agent.",
             lambda c: (c.scroll_to(".lrp-card"), c.spot(".lrp-card"))),
        Beat("b04",
             "Two observer agents isolated in code: Vehicle sees only the "
             "truck, Environment only route and weather.",
             lambda c: (c.spot(".lrp-stage:has-text('Vehicle Agent')"),
                        time.sleep(1.7),
                        c.spot(".lrp-stage:has-text('Environment Agent')"))),
        Beat("b05",
             "A Trust Gate decides what evidence is admissible.",
             lambda c: c.spot(".lrp-stage:has-text('Trust Gate')")),
        Beat("b06",
             "The Risk Assessment Engine — the only LLM, no tools, no action "
             "function — audited by a Verifier.",
             lambda c: (c.spot(".lrp-stage:has-text('Risk Assessment Engine')"),
                        time.sleep(2.1),
                        c.spot(".lrp-stage:has-text('Verifier')"))),
        Beat("b07",
             "Then a deterministic Decision Authority: the only component "
             "allowed to request an action.",
             lambda c: c.spot(".lrp-stage:has-text('Decision Authority')"),
             pad=0.3),
        Beat("b08",
             "Run a normal shipment through the real harness — the same "
             "agents, the same Trust Gate, the same deterministic controller "
             "that grades every check on this system, live.",
             lambda c: (c.spot(None), c.scroll_to(".shipment-form"),
                        c.select(SCENARIO_SELECT, "healthy"),
                        c.spot(SCENARIO_FIELD), time.sleep(1.0), c.spot(None),
                        c.run_and_wait(EVALUATE_BTN))),
        Beat("b09",
             "Every stage agrees — auto-optimise, a hundred percent confidence.",
             lambda c: (c.scroll_to(".final-decision-card"),
                        c.spot(".final-decision-card")), pad=0.4),
    ]))

    # ------------------------------------------------------------- ACT 2
    A.append(Act("act2", "The contradiction", [
        Beat("b10",
             "Now the edge case.",
             lambda c: (c.spot(None), c.scroll_to(".advanced-controls-toggle"),
                        c.click(".advanced-controls-toggle"),
                        c.spot("button:has-text('Verifier Feedback Loop')"),
                        time.sleep(0.7),
                        c.click("button:has-text('Verifier Feedback Loop')"),
                        time.sleep(0.5), c.spot(None))),
        Beat("b11",
             "Cooling reports ON while cargo climbs to eleven and a half "
             "degrees — both cannot be true.",
             lambda c: (c.scroll_to(".shipment-form"),
                        c.select(SCENARIO_SELECT, "sensor_contradiction"),
                        c.spot(COOLING_FIELD), time.sleep(1.5),
                        c.spot(CARGO_FIELD), time.sleep(1.5),
                        c.spot(None))),
        Beat("b12",
             "Both agents observed it independently.",
             None),
        Beat("b13",
             "Run it — the exact same seven stages execute again, in the "
             "exact same order, but this time the evidence disagrees with "
             "itself.",
             lambda c: c.run_and_wait(EVALUATE_BTN), pad=0.3),
        Beat("b14",
             "Correlation catches it deterministically — Evidence Correlation "
             "runs before the Critic ever does.",
             lambda c: (c.scroll_to(".lrp-card"),
                        c.spot(".lrp-stage:has-text('Evidence Correlation')"))),
        Beat("b15",
             "The Verifier rejects the first pass, feeds its reason back. The "
             "Critic revises; the recheck passes clean.",
             lambda c: c.spot(".lrp-stage:has-text('Verifier')")),
        Beat("b16",
             "Confidence falls to seventy-eight percent, computed in code, "
             "never self-reported.",
             lambda c: (c.spot(None), c.scroll_to(".final-decision-card"),
                        c.spot(".final-decision-card"))),
        Beat("b17",
             "The Critic did not decide this — a deterministic rule did. It "
             "requests a human-tier escalation, not an execution.",
             lambda c: (c.spot(None), c.scroll_to(".human-approval-card"),
                        c.spot(".human-approval-card")), pad=0.3),
    ]))

    # ------------------------------------------------------------- ACT 3
    A.append(Act("act3", "Failure, isolation, and policy as data", [
        Beat("b18",
             "Break it: kill the Environment Agent.",
             lambda c: (c.spot(None), c.scroll_to(".shipment-form"),
                        c.select(SCENARIO_SELECT, "missing_sensor"),
                        c.spot(SCENARIO_FIELD), time.sleep(1.0), c.spot(None))),
        Beat("b19",
             "The harness doesn't guess the missing half. It waits for the "
             "run to finish grading what it actually has: insufficient data, "
             "fifty-six percent, no action taken.",
             lambda c: (c.run_and_wait(EVALUATE_BTN),
                        c.scroll_to(".lrp-card"),
                        c.spot(".lrp-stage:has-text('Environment Agent')"),
                        time.sleep(1.6), c.spot(None),
                        c.scroll_to(".final-decision-card"),
                        c.spot(".final-decision-card"))),
        Beat("b20",
             "The same path handles malformed output and stale evidence.",
             None),
        Beat("b21",
             "And the agents cannot act.",
             lambda c: (c.spot(None), c.goto("/simulation"))),
        Beat("b22",
             "Eight paths from an agent to a dispatch action, all eight "
             "blocked — nothing to call.",
             lambda c: (c.scroll_to("h2:has-text('Security Check')"),
                        c.click("button:has-text('Test the safety lock')"),
                        c.click("button:has-text('Show how we tested this')"),
                        c.spot(".probe-list")), pad=0.3),
        Beat("b23",
             "The domain is data, not code.",
             lambda c: (c.spot(None), c.goto("/"),
                        c.scroll_to(".shipment-form"),
                        c.select(SCENARIO_SELECT, "healthy"))),
        Beat("b24",
             "Switch to tyre safety and the signals and risk logic change.",
             lambda c: (c.select(POLICY_SELECT, "tyre_safety"),
                        c.spot(POLICY_FIELD), time.sleep(1.8), c.spot(None))),
        Beat("b25",
             "Zero code changes in the gate, the critic, or the controller "
             "— while this new run finishes executing under the new policy.",
             lambda c: c.run_and_wait(EVALUATE_BTN), pad=0.3),
        Beat("b26",
             "A single agent can't audit its own reasoning, can't deny "
             "itself authority, and can't degrade safely when it fails.",
             lambda c: (c.spot(None), c.goto("/"), c.scroll_top()), pad=0.8),
    ]))

    return A


TITLE_CARD_NARRATION = (
    "This is Fleet-Harness: a trust harness for cold chain fleet operations, "
    "where AI investigates but never decides."
)
END_CARD_NARRATION = (
    "Agents investigate. The critic challenges. Deterministic policy decides."
)


# ------------------------------------------------------------------- http util
def api(method: str, path: str, body: dict | None = None, timeout: float = 20.0):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"{API}{path}", data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
    return json.loads(raw) if raw else None


def url_ok(url: str, timeout: float = 2.0) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.status < 500
    except Exception:
        return False


def wait_until(pred, what: str, timeout: float = 180.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if pred():
                log(f"ready: {what}")
                return True
        except Exception:
            pass
        time.sleep(1.0)
    log(f"TIMED OUT waiting for {what}", "ERROR")
    return False


# ========================================================== STAGE 1 — NARRATION
def find_ffmpeg() -> str:
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
    except ImportError:
        log("ffmpeg not on PATH — installing the imageio-ffmpeg wheel")
        subprocess.run([sys.executable, "-m", "pip", "install", "--quiet",
                        "imageio-ffmpeg"], check=True)
        import imageio_ffmpeg  # noqa: F811
    return imageio_ffmpeg.get_ffmpeg_exe()


FFMPEG = ""


def ff(args: list[str], what: str) -> None:
    """Run ffmpeg, and surface its own error text when it fails."""
    proc = subprocess.run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", *args],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        log(f"ffmpeg FAILED ({what}):\n{proc.stderr.strip()[-2500:]}", "ERROR")
        raise RuntimeError(f"ffmpeg failed: {what}")
    log(f"ffmpeg ok: {what}")


def resolve_fonts() -> None:
    """Pick the first font family actually present on this machine."""
    global FONT_BOLD, FONT_REGULAR, FONT_NAME
    for bold, regular, name in FONT_CANDIDATES:
        if Path(bold).exists() and Path(regular).exists():
            FONT_BOLD, FONT_REGULAR, FONT_NAME = bold, regular, name
            log(f"fonts: {name}")
            return
    log("no known sans font found — cards fall back to ffmpeg's default", "WARN")


def stage_fonts() -> None:
    """libass takes a fontsdir, and a bare relative one avoids the Windows
    drive-colon escaping that breaks the filter parser. The subtitle pass
    already runs with build/ as its working directory."""
    fonts = BUILD_DIR / "fonts"
    fonts.mkdir(parents=True, exist_ok=True)
    for src in (FONT_BOLD, FONT_REGULAR):
        if src and Path(src).exists():
            dst = fonts / Path(src).name
            if not dst.exists():
                shutil.copyfile(src, dst)


def ff_path(path: str) -> str:
    """Escape a Windows path for use inside an ffmpeg filter argument."""
    return path.replace("\\", "/").replace(":", r"\:")


def wav_seconds(path: Path) -> float:
    with wave.open(str(path), "rb") as w:
        return w.getnframes() / float(w.getframerate())


def synthesise(beats: list[Beat], skip: bool) -> None:
    """Windows SAPI, via PowerShell. Offline, no API key, deterministic."""
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    todo = [b for b in beats if not (skip and (AUDIO_DIR / f"{b.key}.wav").exists())]

    if todo:
        script = [
            "Add-Type -AssemblyName System.Speech",
            "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer",
            f"try {{ $s.SelectVoice('{VOICE}') }} catch {{ }}",
            f"$s.Rate = {VOICE_RATE}",
        ]
        for b in todo:
            text = b.say.replace("'", "''")
            out = str(AUDIO_DIR / f"{b.key}.wav").replace("'", "''")
            script.append(f"$s.SetOutputToWaveFile('{out}')")
            script.append(f"$s.Speak('{text}')")
        script.append("$s.Dispose()")

        ps1 = BUILD_DIR / "narrate.ps1"
        ps1.write_text("\n".join(script), encoding="utf-8")
        log(f"synthesising {len(todo)} narration clips with SAPI ({VOICE})")
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
             "-File", str(ps1)],
            capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"SAPI narration failed:\n{proc.stderr[-1500:]}")

    total_words = 0
    for b in beats:
        b.audio = AUDIO_DIR / f"{b.key}.wav"
        if not b.audio.exists():
            raise RuntimeError(f"missing narration clip for beat {b.key}")
        b.audio_secs = wav_seconds(b.audio)
        total_words += len(b.say.split())
    spoken = sum(b.audio_secs for b in beats)
    log(f"narration: {len(beats)} clips, {total_words} words, {spoken:.1f}s spoken "
        f"({total_words / max(spoken, 1) * 60:.0f} wpm)")


# ============================================================= STAGE 2 — SERVERS
class Servers:
    def __init__(self) -> None:
        self.procs: list[tuple[str, subprocess.Popen]] = []

    @staticmethod
    def _python() -> str:
        for c in (BACKEND_DIR / ".venv/Scripts/python.exe",
                  BACKEND_DIR / ".venv/bin/python"):
            if c.exists():
                return str(c)
        return sys.executable

    def start(self) -> None:
        if url_ok(f"{API}/health"):
            log("backend already up on :8000 — reusing")
        else:
            log("starting backend (uvicorn :8000)")
            self._spawn("backend", [self._python(), "-m", "uvicorn",
                                    "app.main:app", "--port", "8000"], BACKEND_DIR)
        if url_ok(UI):
            log("frontend already up on :5173 — reusing")
        else:
            npm = shutil.which("npm.cmd") or shutil.which("npm") or "npm"
            log("starting frontend (vite :5173)")
            self._spawn("frontend", [npm, "run", "dev"], FRONTEND_DIR)

        if not wait_until(lambda: url_ok(f"{API}/health"), "backend /health"):
            raise SystemExit("backend never became ready")
        if not wait_until(lambda: url_ok(UI), "frontend :5173"):
            raise SystemExit("frontend never became ready")
        log(f"health: {api('GET', '/health')}")

    def _spawn(self, name: str, cmd: list[str], cwd: Path) -> None:
        kw = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt" else {}
        self.procs.append((name, subprocess.Popen(
            cmd, cwd=str(cwd), stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, **kw)))

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


def reset_world() -> None:
    """Start from the documented healthy baseline so every number the narration
    quotes is the number that appears on screen."""
    api("POST", "/simulate/reset")
    api("POST", "/policy/active", {"key": "cold_chain"})
    for agent in ("agent_a", "agent_b"):
        api("POST", "/simulate/kill-agent", {"agent": agent, "disabled": False})
    api("POST", "/simulate/stale-signal", {"signal": None})
    api("POST", "/runs")
    api("POST", "/runs")
    log("world + store reset to the healthy baseline")


# ============================================================= STAGE 3 — CAPTURE
# A minimal on-page overlay for the spotlight ring only. Captions are burned in
# by ffmpeg later, so nothing here competes with them.
OVERLAY_JS = r"""
(() => {
  if (window.__vd) return;
  const style = document.createElement('style');
  style.textContent = `
    .vd-spot { outline: 3px solid #38bdf8 !important; outline-offset: 6px;
      border-radius: 14px;
      box-shadow: 0 0 0 9999px rgba(2,6,17,.58), 0 0 40px rgba(56,189,248,.55) !important;
      transition: outline-color .25s ease; }
    .vd-shade { position: fixed; inset: 0; background: #030712; opacity: 0;
      pointer-events: none; z-index: 2147483000; transition: opacity .45s ease; }
    .vd-shade.on { opacity: 1; }
  `;
  const shade = document.createElement('div');
  shade.className = 'vd-shade';
  const mount = () => {
    const root = document.body || document.documentElement;
    if (!root) return false;
    if (!style.isConnected) root.appendChild(style);
    if (!shade.isConnected) root.appendChild(shade);
    return true;
  };
  if (!mount()) document.addEventListener('DOMContentLoaded', mount);
  window.__vd = {
    unspot() {
      if (window.__vdEl) { window.__vdEl.classList.remove('vd-spot'); window.__vdEl = null; }
    },
    fade(on) { mount(); shade.classList.toggle('on', !!on); },
  };
})();
"""


class Ctx:
    """Everything a beat may do to the real application."""

    def __init__(self, page) -> None:
        self.page = page
        self.route: str | None = None
        self.failures = 0

    # -- overlay ------------------------------------------------------------
    def js(self, expr: str):
        try:
            return self.page.evaluate(expr)
        except Exception as exc:
            log(f"js failed: {exc}", "WARN")
            return None

    def spot(self, selector: str | None) -> None:
        self.js("window.__vd && window.__vd.unspot()")
        if not selector:
            return
        try:
            el = self.page.locator(selector).first.element_handle(timeout=4000)
            if el:
                el.evaluate("e => { e.classList.add('vd-spot'); window.__vdEl = e; }")
        except Exception:
            log(f"spotlight target missing: {selector}", "WARN")

    def fade(self, on: bool) -> None:
        self.js(f"window.__vd && window.__vd.fade({'true' if on else 'false'})")
        self.page.wait_for_timeout(500)

    # -- navigation ---------------------------------------------------------
    def goto(self, route: str) -> None:
        if self.route is None:
            self.page.goto(f"{UI}/#{route}", wait_until="domcontentloaded")
            self.page.wait_for_timeout(1800)
        else:
            self.page.evaluate(
                f"window.scrollTo({{top:0}}); location.hash = {json.dumps(route)}")
            self.page.wait_for_timeout(650)
        self.route = route
        log(f"  route -> {route}")

    def scroll_to(self, selector: str) -> None:
        try:
            el = self.page.locator(selector).first.element_handle(timeout=6000)
            if el is None:
                raise RuntimeError("no handle")
            el.evaluate("e => e.scrollIntoView({behavior:'smooth', block:'center'})")
        except Exception:
            self.failures += 1
            log(f"  scroll target missing: {selector}", "WARN")
        self.page.wait_for_timeout(650)

    def scroll_top(self) -> None:
        self.page.evaluate("window.scrollTo({top: 0, behavior: 'smooth'})")
        self.page.wait_for_timeout(500)

    # -- interaction --------------------------------------------------------
    def click(self, selector: str) -> bool:
        try:
            loc = self.page.locator(selector).first
            loc.scroll_into_view_if_needed(timeout=8000)
            self.page.wait_for_timeout(280)
            loc.click(timeout=8000)
            self.page.wait_for_timeout(380)
            log(f"  click {selector}")
            return True
        except Exception as exc:
            self.failures += 1
            log(f"  CLICK FAILED {selector}: {exc}", "WARN")
            return False

    def select(self, selector: str, value: str) -> None:
        try:
            loc = self.page.locator(selector).first
            loc.scroll_into_view_if_needed(timeout=8000)
            loc.select_option(value, timeout=8000)
            self.page.wait_for_timeout(300)
            log(f"  select {selector} = {value}")
        except Exception as exc:
            self.failures += 1
            log(f"  SELECT FAILED {selector}: {exc}", "WARN")

    def set_technical(self, on: bool) -> None:
        label = "Technical" if on else "Simple"
        self.click(f".topbar .mode-toggle button:has-text('{label}')")

    # -- runs ---------------------------------------------------------------
    def latest_run_id(self) -> str | None:
        try:
            recent = api("GET", "/decisions?limit=1")
            return recent[0]["run_id"] if recent else None
        except Exception:
            return None

    def run_and_wait(self, selector: str = ".mc-run-btn") -> dict | None:
        before = self.latest_run_id()
        self.click(selector)
        deadline = time.time() + 25
        while time.time() < deadline:
            rid = self.latest_run_id()
            if rid and rid != before:
                d = api("GET", f"/decisions/{rid}")
                log(f"  RUN {rid}: {d['controller_state']} "
                    f"conf={d['confidence']} excluded="
                    f"{len(d['trace']['excluded_evidence_ids'])} "
                    f"retries={len(d['trace']['retries'])}")
                self.page.wait_for_timeout(1500)
                return d
            time.sleep(0.35)
        log("  no new decision observed", "WARN")
        return None


def capture(acts: list[Act], headed: bool) -> tuple[Path, float, float]:
    """Drive the real UI and record it. Returns (webm, video_t0_wall, wall_end)."""
    from playwright.sync_api import sync_playwright

    if CAPTURE_DIR.exists():
        shutil.rmtree(CAPTURE_DIR, ignore_errors=True)
    CAPTURE_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not headed,
                                    args=["--force-device-scale-factor=1"])
        context = browser.new_context(
            viewport={"width": W, "height": H}, device_scale_factor=1,
            record_video_dir=str(CAPTURE_DIR),
            record_video_size={"width": W, "height": H})
        context.add_init_script(OVERLAY_JS)
        page = context.new_page()
        page.on("pageerror", lambda e: log(f"page error: {e}", "WARN"))

        t_zero = time.time()          # video timeline origin
        ctx = Ctx(page)
        ctx.goto("/")
        page.wait_for_timeout(2200)

        for act in acts:
            log(f"===== {act.key.upper()}: {act.title} =====")
            act.t_start = time.time()
            for beat in act.beats:
                beat.t_start = time.time()
                log(f"  {beat.key}  {beat.say[:78]}")
                if beat.do:
                    try:
                        beat.do(ctx)
                    except Exception as exc:
                        ctx.failures += 1
                        log(f"  beat action failed: {exc}", "WARN")
                # Hold for whatever is left of the spoken line, so the capture is
                # already narration-paced and needs no pause-stripping later.
                spent = time.time() - beat.t_start
                remain = beat.audio_secs + beat.pad + BEAT_GAP - spent
                if remain > 0:
                    time.sleep(remain)
                beat.t_end = time.time()
            ctx.spot(None)
            act.t_end = time.time()

        wall_end = time.time()
        video = page.video
        context.close()
        browser.close()
        path = Path(video.path()) if video else None

    if path is None or not path.exists():
        raise RuntimeError("Playwright produced no video")
    log(f"capture: {path.name} ({path.stat().st_size / 1e6:.0f} MB), "
        f"{ctx.failures} recoverable step failures")
    return path, t_zero, wall_end


# ============================================================ STAGE 4 — ASSEMBLE
def probe_duration(path: Path) -> float:
    proc = subprocess.run(
        [FFMPEG, "-hide_banner", "-i", str(path)],
        capture_output=True, text=True)
    for line in proc.stderr.splitlines():
        if "Duration:" in line:
            hms = line.split("Duration:")[1].split(",")[0].strip()
            h, m, s = hms.split(":")
            return int(h) * 3600 + int(m) * 60 + float(s)
    raise RuntimeError(f"could not read duration of {path}")


def srt_time(t: float) -> str:
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


# Captions sit in a band across the bottom, so they must not eat the frame.
CAP_FONT_PX = 34          # real pixels, because the ASS header sets PlayRes
CAP_SIDE_MARGIN = 210     # px of clear space each side
CAP_BOTTOM_MARGIN = 54
CAP_WRAP_CHARS = 82       # ~2 lines for a typical narration line


def ass_time(t: float) -> str:
    cs = int(round(t * 100))
    h, cs = divmod(cs, 360_000)
    m, cs = divmod(cs, 6_000)
    s, cs = divmod(cs, 100)
    return f"{h:d}:{m:02d}:{s:02d}.{cs:02d}"


def wrap_caption(text: str, width: int = CAP_WRAP_CHARS) -> str:
    """Greedy wrap into ASS hard line breaks, so libass never reflows a line
    into the middle of the screen."""
    lines, current = [], ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if len(candidate) > width and current:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return "\\N".join(lines)


def write_ass(path: Path, cues: list[tuple[float, float, str]]) -> None:
    """An ASS script whose PlayRes matches the frame, so FontSize is in pixels.
    Fed an SRT instead, ffmpeg gives libass a 384x288 canvas and every size is
    silently scaled by 3.75."""
    header = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "WrapStyle: 2",
        "ScaledBorderAndShadow: yes",
        f"PlayResX: {W}",
        f"PlayResY: {H}",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, "
        "ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, "
        "MarginL, MarginR, MarginV, Encoding",
        # BorderStyle 3 = opaque box drawn in OutlineColour (&H30.. = ~81% opaque)
        f"Style: Caption,{FONT_NAME},{CAP_FONT_PX},&H00F1F5F9,&H00F1F5F9,"
        f"&H30030712,&H30030712,-1,0,0,0,100,100,0,0,3,7,0,2,"
        f"{CAP_SIDE_MARGIN},{CAP_SIDE_MARGIN},{CAP_BOTTOM_MARGIN},1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    events = [
        f"Dialogue: 0,{ass_time(start)},{ass_time(end)},Caption,,0,0,0,,"
        f"{wrap_caption(text)}"
        for start, end, text in cues
    ]
    path.write_text("\n".join(header + events) + "\n", encoding="utf-8", newline="\n")
    log(f"captions: {len(cues)} cues at {CAP_FONT_PX}px on a {W}x{H} canvas")


def make_card(path: Path, seconds: float,
              lines: list[tuple[str, int, str, bool]]) -> None:
    """A card is a solid backdrop plus drawtext lines:
    (text, size, colour, bold)."""
    draws = []
    for i, (text, size, colour, bold) in enumerate(lines):
        safe = (text.replace("\\", "\\\\").replace(":", "\\:")
                    .replace("'", "’").replace("%", "\\%"))
        y = (f"(h/2)-{sum(l[1] for l in lines) * 0.9 / 2:.0f}"
             f"+{sum(l[1] for l in lines[:i]) * 1.55:.0f}")
        face = FONT_BOLD if bold else FONT_REGULAR
        font = f":fontfile='{ff_path(face)}'" if face else ""
        draws.append(
            f"drawtext=text='{safe}'{font}:fontcolor={colour}:fontsize={size}"
            f":x=(w-text_w)/2:y={y}"
            f":alpha='if(lt(t,0.5),t/0.5,if(lt(t,{seconds - 0.6:.2f}),1,"
            f"max(0,({seconds:.2f}-t)/0.6)))'")
    vf = ",".join(draws)
    ff(["-f", "lavfi", "-i", f"color=c=0x070c18:s={W}x{H}:d={seconds}:r={FPS}",
        "-vf", vf, "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-pix_fmt", "yuv420p", str(path)], f"card {path.name}")


def cut_segment(src: Path, dst: Path, start: float, end: float) -> None:
    ff(["-ss", f"{start:.3f}", "-to", f"{end:.3f}", "-i", str(src),
        "-vf", f"scale={W}:{H}:flags=lanczos,fps={FPS},setpts=PTS-STARTPTS",
        "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-pix_fmt", "yuv420p", str(dst)], f"cut {dst.name}")


def assemble(acts: list[Act], webm: Path, t_zero: float, wall_end: float) -> None:
    BUILD_DIR.mkdir(parents=True, exist_ok=True)

    # Playwright writes a variable-rate webm; map wall clock onto its timeline
    # by measuring both, instead of assuming they run at the same rate.
    vid_secs = probe_duration(webm)
    wall_secs = wall_end - t_zero
    scale = vid_secs / wall_secs
    log(f"capture {vid_secs:.2f}s video / {wall_secs:.2f}s wall (scale {scale:.4f})")

    def vt(wall: float) -> float:
        return max(0.0, (wall - t_zero) * scale)

    # ---- 1. the five pieces ------------------------------------------------
    title = BUILD_DIR / "seg_title.mp4"
    end = BUILD_DIR / "seg_end.mp4"
    title_secs = TITLE_AUDIO_SECS + 1.6
    end_secs = END_AUDIO_SECS + 2.2

    make_card(title, title_secs, [
        ("FLEET-HARNESS", 96, "0xf8fafc", True),
        ("Cold-chain dispatch under a trust harness", 42, "0x94a3b8", False),
        ("Agents investigate  -  The critic challenges  -  Deterministic policy decides",
         30, "0x38bdf8", False),
    ])
    make_card(end, end_secs, [
        ("Agents investigate.", 76, "0xf8fafc", True),
        ("The critic challenges.", 76, "0xf8fafc", True),
        ("Deterministic policy decides.", 76, "0x38bdf8", True),
    ])

    segments = [title]
    for act in acts:
        seg = BUILD_DIR / f"seg_{act.key}.mp4"
        cut_segment(webm, seg, vt(act.t_start), vt(act.t_end))
        segments.append(seg)
    segments.append(end)

    durations = [probe_duration(s) for s in segments]
    log("segments: " + ", ".join(f"{s.stem}={d:.1f}s" for s, d in zip(segments, durations)))

    # ---- 2. cross-fade them into one timeline ------------------------------
    inputs: list[str] = []
    for s in segments:
        inputs += ["-i", str(s)]

    filters, prev, offset = [], "0:v", 0.0
    offsets = [0.0]                     # where each segment starts in the output
    for i in range(1, len(segments)):
        offset += durations[i - 1] - XFADE
        offsets.append(offset)
        out = f"vx{i}"
        filters.append(f"[{prev}][{i}:v]xfade=transition=fade:duration={XFADE}"
                       f":offset={offset:.3f}[{out}]")
        prev = out
    total = offset + durations[-1]

    body = BUILD_DIR / "video_only.mp4"
    ff([*inputs, "-filter_complex", ";".join(filters), "-map", f"[{prev}]",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-pix_fmt", "yuv420p", "-r", str(FPS), str(body)], "xfade chain")
    log(f"assembled timeline: {total:.1f}s")

    # ---- 3. narration onto that timeline -----------------------------------
    # Each clip is delayed to where its beat actually lands in the output.
    clips: list[tuple[Path, float]] = [(TITLE_AUDIO, 0.8)]
    for a_i, act in enumerate(acts, start=1):
        seg_start_out = offsets[a_i]
        seg_start_vid = vt(act.t_start)
        for beat in act.beats:
            at = seg_start_out + (vt(beat.t_start) - seg_start_vid)
            clips.append((beat.audio, at))
    clips.append((END_AUDIO, offsets[-1] + 0.9))

    a_inputs: list[str] = []
    a_filters: list[str] = []
    for i, (clip, at) in enumerate(clips):
        a_inputs += ["-i", str(clip)]
        a_filters.append(f"[{i}:a]aresample=48000,adelay={int(at * 1000)}|"
                         f"{int(at * 1000)}[a{i}]")
    mix = "".join(f"[a{i}]" for i in range(len(clips)))
    a_filters.append(f"{mix}amix=inputs={len(clips)}:normalize=0:dropout_transition=0,"
                     f"alimiter=limit=0.95,apad,atrim=0:{total:.3f}[aout]")

    narration = BUILD_DIR / "narration.m4a"
    ff([*a_inputs, "-filter_complex", ";".join(a_filters), "-map", "[aout]",
        "-c:a", "aac", "-b:a", "192k", str(narration)], "narration mix")

    # ---- 4. captions -------------------------------------------------------
    cues: list[str] = []
    timed_cues: list[tuple[float, float, str]] = []
    n = 1

    def cue(text: str, start: float, dur: float) -> None:
        nonlocal n
        cues.append(f"{n}\n{srt_time(start)} --> {srt_time(start + dur)}\n{text}\n")
        timed_cues.append((start, start + dur, text))
        n += 1

    for a_i, act in enumerate(acts, start=1):
        seg_start_out = offsets[a_i]
        seg_start_vid = vt(act.t_start)
        for beat in act.beats:
            at = seg_start_out + (vt(beat.t_start) - seg_start_vid)
            cue(beat.caption or beat.say, at, beat.audio_secs + 0.25)

    srt = BUILD_DIR / "captions.srt"
    srt.write_text("\n".join(cues), encoding="utf-8", newline="\n")

    # Burn an ASS file rather than the SRT. ffmpeg hands libass an SRT with the
    # default 384x288 script canvas, so a font size meant for 1080p is scaled up
    # 3.75x and the captions swallow the screen. An ASS header with PlayRes set
    # to the real frame size makes FontSize mean pixels.
    stage_fonts()
    write_ass(BUILD_DIR / "captions.ass", timed_cues)

    # libass path handling on Windows is brittle, so run ffmpeg inside build/
    # and reference the subtitle file by bare name.
    cwd = os.getcwd()
    try:
        os.chdir(BUILD_DIR)
        proc = subprocess.run(
            [FFMPEG, "-hide_banner", "-loglevel", "error", "-y",
             "-i", body.name, "-i", narration.name,
             "-filter_complex",
             "[0:v]subtitles=captions.ass:fontsdir=fonts[v]",
             "-map", "[v]", "-map", "1:a",
             "-c:v", "libx264", "-preset", "slow", "-crf", "19",
             "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.1",
             "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
             "-shortest", str(OUTPUT)],
            capture_output=True, text=True)
    finally:
        os.chdir(cwd)
    if proc.returncode != 0:
        log(f"ffmpeg FAILED (final mux):\n{proc.stderr.strip()[-2500:]}", "ERROR")
        raise RuntimeError("final encode failed")
    log("ffmpeg ok: captions + mux")


TITLE_AUDIO = AUDIO_DIR / "card-title.wav"
END_AUDIO = AUDIO_DIR / "card-end.wav"
TITLE_AUDIO_SECS = 0.0
END_AUDIO_SECS = 0.0


# ------------------------------------------------------------------------ main
def main() -> int:
    global LOG, FFMPEG, TITLE_AUDIO_SECS, END_AUDIO_SECS

    ap = argparse.ArgumentParser(description="Fleet-Harness 3-minute demo video")
    ap.add_argument("--no-servers", action="store_true")
    ap.add_argument("--skip-capture", action="store_true")
    ap.add_argument("--skip-tts", action="store_true")
    ap.add_argument("--headed", action="store_true")
    ap.add_argument("--keep-build", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    DEMO_DIR.mkdir(parents=True, exist_ok=True)
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    LOG = Log(LOG_PATH)

    try:
        acts = build_acts()
        beats = [b for a in acts for b in a.beats]
        cards = [Beat("card-title", TITLE_CARD_NARRATION),
                 Beat("card-end", END_CARD_NARRATION)]

        words = sum(len(b.say.split()) for b in beats + cards)
        log(f"Fleet-Harness demo video — {len(acts)} acts, {len(beats)} beats, "
            f"{words} narration words")
        for a in acts:
            log(f"  {a.key}: {len(a.beats)} beats — {a.title}")

        FFMPEG = find_ffmpeg()
        log(f"ffmpeg: {FFMPEG}")
        resolve_fonts()

        synthesise(beats + cards, skip=args.skip_tts)
        TITLE_AUDIO_SECS = cards[0].audio_secs
        END_AUDIO_SECS = cards[1].audio_secs

        est = (sum(b.audio_secs + b.pad + BEAT_GAP for b in beats)
               + TITLE_AUDIO_SECS + 1.6 + END_AUDIO_SECS + 2.2 - 4 * XFADE)
        log(f"estimated finished length: {est:.0f}s ({est / 60:.2f} min)")

        if args.dry_run:
            for b in beats:
                log(f"  {b.key}  {b.audio_secs:5.2f}s  {b.say}")
            return 0

        state = BUILD_DIR / "capture_state.json"
        servers = Servers()
        started = False
        try:
            if args.skip_capture:
                if not state.exists():
                    raise SystemExit("--skip-capture but no previous capture found")
                saved = json.loads(state.read_text(encoding="utf-8"))
                webm = Path(saved["webm"])
                t_zero, wall_end = saved["t_zero"], saved["wall_end"]
                for a in acts:
                    a.t_start, a.t_end = saved["acts"][a.key]
                for b in beats:
                    b.t_start, b.t_end = saved["beats"][b.key]
                log(f"reusing capture {webm.name}")
            else:
                if not args.no_servers:
                    servers.start()
                    started = True
                else:
                    if not wait_until(lambda: url_ok(f"{API}/health"), "backend", 60):
                        return 2
                    if not wait_until(lambda: url_ok(UI), "frontend", 60):
                        return 2
                reset_world()
                webm, t_zero, wall_end = capture(acts, args.headed)
                state.write_text(json.dumps({
                    "webm": str(webm), "t_zero": t_zero, "wall_end": wall_end,
                    "acts": {a.key: [a.t_start, a.t_end] for a in acts},
                    "beats": {b.key: [b.t_start, b.t_end] for b in beats},
                }, indent=1), encoding="utf-8")
        finally:
            if started:
                servers.stop()

        assemble(acts, webm, t_zero, wall_end)

        final_secs = probe_duration(OUTPUT)
        size_mb = OUTPUT.stat().st_size / 1e6
        log(f"DONE  {OUTPUT}")
        log(f"      {final_secs:.1f}s ({final_secs / 60:.2f} min), {size_mb:.1f} MB, "
            f"{W}x{H} H.264 + AAC")

        if not args.keep_build:
            shutil.rmtree(CAPTURE_DIR, ignore_errors=True)
            for f in BUILD_DIR.glob("seg_*.mp4"):
                f.unlink(missing_ok=True)
            (BUILD_DIR / "video_only.mp4").unlink(missing_ok=True)
            log("cleaned intermediate segments (keep them with --keep-build)")
        return 0
    finally:
        if LOG:
            LOG.close()


if __name__ == "__main__":
    raise SystemExit(main())
