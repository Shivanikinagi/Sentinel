// Proves the harness is domain-independent — swapping the active policy pack
// changes what the Trust Gate requires and how the Risk Assessment Engine
// reasons, live, without touching gate/critic/controller code.
import { useEffect, useState } from "react";
import { api } from "../api";
import { useFleet } from "../FleetDataContext";
import { signalLabel } from "../humanize";
import type { PolicyPackInfo } from "../types";

export function PolicyPackCard() {
  const { decision } = useFleet();
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

  return (
    <div className="panel">
      <h2>Policy Engine</h2>
      <p className="stat-sub" style={{ marginBottom: 0 }}>
        Deterministic domain rules the Gate, Correlation Engine, and Risk Assessment Engine reason against.
        {decision && <> Last run used <strong>{decision.policy_pack}</strong>.</>}
      </p>
      <div className="policy-pack-grid">
        {packs.map((p) => (
          <div
            key={p.key}
            className={`policy-pack-card${p.key === active ? " active" : ""}`}
            onClick={() => select(p.key)}
            role="button"
          >
            <div className="policy-pack-card-title">
              {p.label}
              {p.key === active && <span className="badge badge-info">ACTIVE</span>}
            </div>
            <div className="policy-pack-card-domain">{p.domain}</div>
            <div className="policy-pack-card-desc">{p.description}</div>
            <div className="policy-pack-signals">
              {p.required_signals.map((s) => (
                <span key={s} className="chip fresh">{signalLabel(s)}</span>
              ))}
            </div>
          </div>
        ))}
        {packs.length === 0 && <div className="empty">Loading policy packs…</div>}
      </div>
    </div>
  );
}
