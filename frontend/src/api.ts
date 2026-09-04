import type {
  ActionRequest,
  AuditRecord,
  ControllerDecision,
  HarnessMetrics,
  PolicyPackInfo,
  ProbeResult,
  VehicleTrend,
  WorldState,
} from "./types";

const BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

export const api = {
  health: () => req<{ ok: boolean; critic_backend: string; model: string }>("/health"),
  run: (policyPack?: string) =>
    req<ControllerDecision>(`/runs${policyPack ? `?policy_pack=${policyPack}` : ""}`, { method: "POST" }),
  recentDecisions: (limit = 1) =>
    req<ControllerDecision[]>(`/decisions?limit=${limit}`),
  decision: (runId: string) => req<ControllerDecision>(`/decisions/${runId}`),
  state: () => req<WorldState>("/state"),
  audit: (limit = 30) => req<AuditRecord[]>(`/audit?limit=${limit}`),
  pending: () => req<ActionRequest[]>("/actions/pending"),

  metrics: () => req<HarnessMetrics>("/metrics"),
  policyPacks: () => req<PolicyPackInfo[]>("/policy/packs"),
  activePolicyPack: () => req<PolicyPackInfo>("/policy/active"),
  setActivePolicyPack: (key: string) =>
    req<PolicyPackInfo>("/policy/active", { method: "POST", body: JSON.stringify({ key }) }),
  vehicleTrend: (vehicleId: string, signal: string, limit = 8) =>
    req<VehicleTrend>(`/vehicles/${vehicleId}/trend?signal=${signal}&limit=${limit}`),
  transientError: () => req("/simulate/transient-error", { method: "POST" }),

  scenario: (name: string) =>
    req("/simulate/scenario", { method: "POST", body: JSON.stringify({ name }) }),
  killAgent: (agent: "agent_a" | "agent_b", disabled: boolean) =>
    req("/simulate/kill-agent", {
      method: "POST",
      body: JSON.stringify({ agent, disabled }),
    }),
  corruptLlm: () => req("/simulate/corrupt-llm", { method: "POST" }),
  staleSignal: (signal: string | null) =>
    req("/simulate/stale-signal", {
      method: "POST",
      body: JSON.stringify({ signal }),
    }),
  reset: () => req("/simulate/reset", { method: "POST" }),
  unauthorizedAction: () =>
    req<ProbeResult>("/simulate/unauthorized-action", { method: "POST" }),

  emergencyOverride: () => req("/simulate/emergency-override", { method: "POST" }),
  sensorDrift: (temp = 14.5) => req(`/simulate/sensor-drift?cargo_temp=${temp}`, { method: "POST" }),
  tripCircuitBreaker: () => req("/simulate/circuit-breaker", { method: "POST" }),
  approve: (id: string, approver: string) =>
    req<ActionRequest>(`/actions/${id}/approve`, {
      method: "POST",
      body: JSON.stringify({ approver }),
    }),
  reject: (id: string, approver: string, reason: string) =>
    req<ActionRequest>(`/actions/${id}/reject`, {
      method: "POST",
      body: JSON.stringify({ approver, reason }),
    }),
};
