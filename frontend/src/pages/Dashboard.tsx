import { useFleet } from "../FleetDataContext";
import {
  ControllerBanner, PendingActions, PipelineStepper, StatCard,
} from "../components";
import { STATE_META, relativeTime } from "../humanize";
import { ActivityIcon, ShieldIcon } from "../icons";
import { Link } from "react-router-dom";

export default function Dashboard() {
  const {
    decision, history, world, actions, technical, approve, reject, runNow, busy,
  } = useFleet();

  const runs = history.length;
  const avgConfidence = runs
    ? Math.round((history.reduce((s, d) => s + d.confidence, 0) / runs) * 100)
    : 0;
  const autoCount = history.filter((d) => d.controller_state === "AUTO_OPTIMIZE").length;
  const uptime = runs ? Math.round((autoCount / runs) * 1000) / 10 : 0;
  const agentsReporting = decision?.trace.agents_reporting.length ?? 0;

  return (
    <div className="page">
      <div className="stat-grid">
        <StatCard label="Checks Run" value={String(runs)} sub="in current session" icon={<ActivityIcon size={15} />} />
        <StatCard
          label="Avg. Confidence" value={`${avgConfidence}%`} sub="across recent runs"
          tone={avgConfidence >= 85 ? "good" : avgConfidence >= 50 ? "warn" : "bad"}
        />
        <StatCard
          label="Auto-Optimize Rate" value={`${uptime}%`} sub="healthy decision share"
          tone={uptime >= 85 ? "good" : uptime >= 50 ? "warn" : "bad"} icon={<ShieldIcon size={15} />}
        />
        <StatCard
          label="Pending Approvals" value={String(actions.length)} sub={actions.length ? "needs a human" : "all clear"}
          tone={actions.length ? "warn" : "good"}
        />
      </div>

      <ControllerBanner d={decision} technical={technical} />

      <div className="dash-grid">
        <div className="panel">
          <div className="panel-head-row">
            <h2>Live Decision Log</h2>
            <Link className="link-btn" to="/audit">View all →</Link>
          </div>
          {history.length === 0 ? (
            <div className="empty">No runs yet. Trigger a check from Simulation Lab.</div>
          ) : (
            <div className="decision-list">
              {history.slice(0, 8).map((d) => {
                const tone = STATE_META[d.controller_state].tone;
                return (
                  <div className="decision-row" key={d.run_id}>
                    <span className={`dot dot-${tone}`} />
                    <span className="decision-vehicle">{d.vehicle_id}</span>
                    <span className={`status-pill tone-${tone} sm`}>{d.controller_state}</span>
                    <span className="decision-conf">{Math.round(d.confidence * 100)}%</span>
                    <span className="decision-time">{relativeTime(d.timestamp)}</span>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        <div className="panel">
          <h2>Pipeline Snapshot{technical && <span className="tech-caption"> · Sensors → Gate → Critic → Controller</span>}</h2>
          {decision ? (
            <PipelineStepper d={decision} technical={technical} />
          ) : (
            <div className="empty">Run a check to see the pipeline flow.</div>
          )}
          <div className="agent-summary">
            <div className="agent-summary-item">
              <span className={`dot ${agentsReporting === 2 ? "dot-good" : agentsReporting === 1 ? "dot-warn" : "dot-bad"}`} />
              {agentsReporting}/2 agents reporting
            </div>
            <div className="agent-summary-item">
              <span className={`dot ${world?.switches.corrupt_critic ? "dot-warn" : "dot-good"}`} />
              Critic {world?.switches.corrupt_critic ? "glitch armed" : "nominal"}
            </div>
          </div>
          <button className="primary" style={{ marginTop: 14 }} disabled={busy} onClick={runNow}>
            Run check now
          </button>
        </div>
      </div>

      <PendingActions actions={actions} onApprove={approve} onReject={reject} technical={technical} />
    </div>
  );
}
