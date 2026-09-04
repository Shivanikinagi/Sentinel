// The isolation guarantee almost nobody demos live: Agent A has no callable
// path to Agent B's tools. Reuses POST /simulate/unauthorized-tool, which
// already really attempts the call and really catches ToolAccessDeniedError
// (see backend/app/tools.py) — nothing here is staged.
import { useState } from "react";
import { api } from "../api";
import { XCircle, ZapIcon } from "../icons";

export function IsolationDemoCard() {
  const [result, setResult] = useState<{ blocked: boolean; detail: string } | null>(null);
  const [busy, setBusy] = useState(false);

  const run = async () => {
    setBusy(true);
    try {
      const r = await api.unauthorizedTool();
      setResult(r);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="panel">
      <h2>Isolation Proof</h2>
      <p className="stat-sub" style={{ marginBottom: 10 }}>
        Vehicle Agent has no code path to Environment Agent's tools — not a permission
        check, a missing reference entirely.
      </p>
      <button className="warn" disabled={busy} onClick={run}>
        <ZapIcon size={12} /> Try: Vehicle Agent → Environment Weather API
      </button>

      {result && (
        <div className="isolation-result">
          <div className="isolation-flow">
            <span className="isolation-node">Vehicle Agent</span>
            <span className="isolation-arrow">tries →</span>
            <span className="isolation-node">Environment Weather API</span>
          </div>
          <div className={`isolation-outcome ${result.blocked ? "blocked" : "exposed"}`}>
            {result.blocked ? <XCircle size={16} /> : null}
            {result.blocked ? "DENIED" : "EXPOSED"}
          </div>
          <div className="tech-caption">{result.detail}</div>
        </div>
      )}
    </div>
  );
}
