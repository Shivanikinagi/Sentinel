// Proves the harness is domain-independent — swapping the active policy pack
// changes what the Trust Gate requires and how the Risk Assessment Engine
// reasons, live, without touching gate/critic/controller code. Kept to an
// active label + a row of pills — no per-pack description dump.
import { useEffect, useState } from "react";
import { api } from "../api";
import type { PolicyPackInfo } from "../types";

export function PolicyPackCard() {
  const [packs, setPacks] = useState<PolicyPackInfo[]>([]);
  const [active, setActive] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = () => {
    api.policyPacks().then(setPacks).catch(() => {});
    api.activePolicyPack().then((p) => setActive(p.key)).catch(() => {});
  };

  useEffect(load, []);

  const select = async (key: string) => {
    if (busy || key === active) return;
    setBusy(true);
    try {
      await api.setActivePolicyPack(key);
      setActive(key);
    } finally {
      setBusy(false);
    }
  };

  const activeLabel = packs.find((p) => p.key === active)?.label ?? active ?? "—";

  return (
    <div className="panel">
      <h2>Policy Engine</h2>
      <div className="panel-sub" style={{ marginBottom: 10 }}>The runtime stays the same — only the policy changes.</div>
      <div className="policy-pill-row">
        <span className="policy-pill-label">Active</span>
        <span className="badge badge-info">{activeLabel}</span>
      </div>
      <div className="policy-pill-row" style={{ marginTop: 8 }}>
        <span className="policy-pill-label">Available</span>
        {packs.map((p) => (
          <button
            key={p.key}
            className={`policy-pill${p.key === active ? " active" : ""}`}
            disabled={busy}
            onClick={() => select(p.key)}
            title={p.description}
          >
            {p.key === active ? "●" : "○"} {p.label}
          </button>
        ))}
        {packs.length === 0 && <span className="empty">Loading…</span>}
      </div>
    </div>
  );
}
