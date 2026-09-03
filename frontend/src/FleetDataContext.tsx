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
  setMode: (tech: boolean) => void;
  runNow: () => void;
  approve: (id: string) => void;
  reject: (id: string) => void;
  runProbe: () => void;
  setScenario: (name: string) => void;
  killAgent: (agent: "agent_a" | "agent_b", disabled: boolean) => void;
  corruptLlm: () => void;
  staleSignal: (signal: string | null) => void;
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
      /* backend not up yet; keep last state */
    }
  }, []);

  useEffect(() => {
    api.health().then((h) => setBackend(h.critic_backend)).catch(() => setBackend("offline"));
    refresh();
    const t = setInterval(refresh, 1500);
    return () => clearInterval(t);
  }, [refresh]);

  const guard = async (fn: () => Promise<unknown>, msg: string) => {
    setBusy(true);
    try {
      await fn();
      await refresh();
      flash(msg);
    } catch (e) {
      flash(`Something went wrong: ${(e as Error).message}`);
    } finally {
      setBusy(false);
    }
  };

  const sw = world?.switches;

  const value: FleetData = {
    decision, history, world, actions, audit, backend, probe, toast, busy, technical,
    setMode,
    runNow: () => guard(async () => setDecision(await api.run()), "Check complete"),
    approve: (id) => guard(() => api.approve(id, "ops@fleet"), "Approved and carried out"),
    reject: (id) => {
      const reason = prompt("Why are you rejecting this?") ?? "rejected by operator";
      return guard(() => api.reject(id, "ops@fleet", reason), "Rejected");
    },
    runProbe: () => guard(async () => setProbe(await api.unauthorizedAction()), "Security check complete"),
    setScenario: (name) => guard(() => api.scenario(name), name === "compound_risk" ? "Simulating a risky situation" : "Back to normal conditions"),
    killAgent: (agent, disabled) => guard(
      () => api.killAgent(agent, disabled),
      disabled ? `${agent === "agent_a" ? "Truck sensors" : "Route sensors"} disconnected` : `${agent === "agent_a" ? "Truck sensors" : "Route sensors"} reconnected`
    ),
    corruptLlm: () => guard(() => api.corruptLlm(), "Next AI answer will be broken on purpose"),
    staleSignal: (signal) => guard(
      () => api.staleSignal(signal),
      signal ? "Cargo temperature reading is now old" : "Old data cleared"
    ),
    reset: () => guard(() => api.reset(), "Everything reset"),
  };
  void sw;

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
