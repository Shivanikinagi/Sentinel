import {
  createContext, useCallback, useContext, useEffect, useState, type ReactNode,
} from "react";
import { api } from "./api";
import type {
  ActionRequest, AuditRecord, ControllerDecision, ProbeResult, WorldState,
} from "./types";

const VIEW_KEY = "fleet-harness-view-mode";

interface FleetData {
  decision: ControllerDecision | null;
  history: ControllerDecision[];
  world: WorldState | null;
  actions: ActionRequest[];
  audit: AuditRecord[];
  backend: string;
  probe: ProbeResult | null;
  toast: string | null;
  busy: boolean;
  technical: boolean;
  survivedFailuresCount: number;
  timeLapseSpeed: number;
  autoPlayActive: boolean;
  setTimeLapseSpeed: (speed: number) => void;
  startAutoPlay: () => void;
  setMode: (tech: boolean) => void;
  runNow: () => void;
  approve: (id: string) => void;
  reject: (id: string) => void;
  runProbe: () => void;
  setScenario: (name: string) => void;
  killAgent: (agent: "agent_a" | "agent_b", disabled: boolean) => void;
  corruptLlm: () => void;
  staleSignal: (signal: string | null) => void;
  emergencyOverride: () => void;
  sensorDrift: (temp?: number) => void;
  tripCircuitBreaker: () => void;
  triggerTransientError: () => void;
  reset: () => void;
}

const Ctx = createContext<FleetData | null>(null);

export function FleetDataProvider({ children }: { children: ReactNode }) {
  const [decision, setDecision] = useState<ControllerDecision | null>(null);
  const [history, setHistory] = useState<ControllerDecision[]>([]);
  const [world, setWorld] = useState<WorldState | null>(null);
  const [actions, setActions] = useState<ActionRequest[]>([]);
  const [audit, setAudit] = useState<AuditRecord[]>([]);
  const [backend, setBackend] = useState<string>("…");
  const [probe, setProbe] = useState<ProbeResult | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  // Counts the failures actually injected in THIS session, so the topbar badge
  // is a real count rather than a seeded-looking number.
  const [survivedFailuresCount, setSurvivedFailuresCount] = useState(0);
  const [timeLapseSpeed, setTimeLapseSpeed] = useState(1);
  const [autoPlayActive, setAutoPlayActive] = useState(false);

  const [technical, setTechnical] = useState<boolean>(() => {
    try { return localStorage.getItem(VIEW_KEY) === "technical"; } catch { return false; }
  });

  const setMode = (tech: boolean) => {
    setTechnical(tech);
    try { localStorage.setItem(VIEW_KEY, tech ? "technical" : "simple"); } catch { /* ignore */ }
  };

  const flash = (m: string) => {
    setToast(m);
    setTimeout(() => setToast(null), 2500);
  };

  const refresh = useCallback(async () => {
    try {
      const [ws, decisions, pending, aud] = await Promise.all([
        api.state(), api.recentDecisions(20), api.pending(), api.audit(60),
      ]);
      setWorld(ws);
      setHistory(decisions);
      setDecision(decisions[0] ?? null);
      setActions(pending);
      setAudit(aud);
    } catch {
      /* backend not up yet */
    }
  }, []);

  useEffect(() => {
    api.health().then((h) => setBackend(h.critic_backend)).catch(() => setBackend("offline"));
    refresh();
    const t = setInterval(refresh, 1500 / timeLapseSpeed);
    return () => clearInterval(t);
  }, [refresh, timeLapseSpeed]);

  // A totally empty dashboard (all zeros, "no data yet" everywhere) reads as
  // broken, not idle. Seed two healthy runs on first load if the backend has
  // no history yet, so metrics/trend/analytics have something real to show.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const existing = await api.recentDecisions(1);
        if (!cancelled && existing.length === 0) {
          await api.run();
          await api.run();
        }
      } catch {
        /* backend not up yet — the regular poll will catch it later */
      }
      if (!cancelled) refresh();
    })();
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const guard = async (fn: () => Promise<unknown>, msg: string, incrementFailure = false) => {
    setBusy(true);
    try {
      await fn();
      await refresh();
      if (incrementFailure) {
        setSurvivedFailuresCount((prev) => prev + 1);
      }
      flash(msg);
    } catch (e) {
      flash(`Error: ${(e as Error).message}`);
    } finally {
      setBusy(false);
    }
  };

  const startAutoPlay = async () => {
    if (autoPlayActive) return;
    setAutoPlayActive(true);
    flash("▶ Starting Auto-Play Presentation Mode...");

    const steps = [
      { name: "healthy", msg: "Scene 1: Healthy Run" },
      { name: "compound_risk", msg: "Scene 2: Contradiction Risk" },
      { action: () => api.killAgent("agent_a", true), msg: "Scene 3: Agent Blackout" },
      { action: () => api.corruptLlm(), msg: "Scene 4: Corrupt LLM Payload" },
      { action: () => api.staleSignal("cargo_temperature"), msg: "Scene 5: Stale Evidence" },
      { action: () => api.reset(), msg: "Scene 6: Reset to Healthy" },
    ];

    for (const step of steps) {
      setBusy(true);
      flash(step.msg);
      if (step.name) {
        await api.scenario(step.name);
      } else if (step.action) {
        await step.action();
      }
      await api.run();
      await refresh();
      setBusy(false);
      await new Promise((r) => setTimeout(r, 2500));
    }
    setAutoPlayActive(false);
    flash("✓ Auto-Play Presentation Complete!");
  };

  const value: FleetData = {
    decision, history, world, actions, audit, backend, probe, toast, busy, technical,
    survivedFailuresCount, timeLapseSpeed, autoPlayActive, setTimeLapseSpeed, startAutoPlay,
    setMode,
    runNow: () => guard(async () => setDecision(await api.run()), "Harness Check Complete"),
    approve: (id) => guard(() => api.approve(id, "ops@fleet"), "Approved & Carried Out"),
    reject: (id) => {
      const reason = prompt("Why are you rejecting this?") ?? "rejected by operator";
      return guard(() => api.reject(id, "ops@fleet", reason), "Rejected");
    },
    runProbe: () => guard(async () => setProbe(await api.unauthorizedAction()), "Security Probe Passed", true),
    setScenario: (name) => guard(() => api.scenario(name), name === "compound_risk" ? "Simulating Contradiction Anomaly" : "Healthy Operations"),
    killAgent: (agent, disabled) => guard(
      () => api.killAgent(agent, disabled),
      disabled ? `${agent === "agent_a" ? "Truck" : "Route"} Sensor Offline` : "Sensor Restored",
      disabled
    ),
    corruptLlm: () => guard(() => api.corruptLlm(), "Corrupt LLM Output Injected", true),
    staleSignal: (signal) => guard(
      () => api.staleSignal(signal),
      signal ? "Telemetry Backdated to Stale" : "Stale Flag Cleared",
      Boolean(signal)
    ),
    emergencyOverride: () => guard(() => api.emergencyOverride(), "🚨 EMERGENCY HUMAN OVERRIDE ENGAGED", true),
    sensorDrift: (temp = 14.5) => guard(() => api.sensorDrift(temp), `Sensor Drift: Temp set to ${temp}°C`, true),
    tripCircuitBreaker: () => guard(() => api.tripCircuitBreaker(), "⚡ LLM Circuit Breaker Tripped to OPEN", true),
    triggerTransientError: () => guard(() => api.transientError(), "↻ Risk Assessment Engine will fail once, then retry", true),
    reset: () => guard(() => api.reset(), "Harness State Reset"),
  };

  return (
    <Ctx.Provider value={value}>
      {children}
      {toast && <div className="toast">{toast}</div>}
    </Ctx.Provider>
  );
}

export function useFleet(): FleetData {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useFleet must be used within FleetDataProvider");
  return ctx;
}
