import { useFleet } from "../FleetDataContext";
import { StatCard } from "../components";
import { BarMini, Donut, Sparkline } from "../charts";

export default function Analytics() {
  const { history, audit, technical } = useFleet();

  const chronological = [...history].reverse();
  const confidenceSeries = chronological.map((d) => d.confidence);

  const counts = { AUTO_OPTIMIZE: 0, INSUFFICIENT_DATA: 0, CRITICAL_HALT: 0 };
  history.forEach((d) => { counts[d.controller_state] += 1; });
  const total = history.length || 1;

  const criticRejections = history.filter((d) => d.critic_rejected).length;
  const contradictions = history.filter((d) => d.risk_matrix?.contradiction_detected).length;
  const avgConfidence = history.reduce((s, d) => s + d.confidence, 0) / total;

  const securityEvents = audit.filter((r) => r.event_type === "security_probe");
  const securityPassRate = securityEvents.length
    ? securityEvents.filter((r) => r.payload.blocked).length / securityEvents.length
    : 1;

  return (
    <div className="page">
      <div className="stat-grid">
        <StatCard label="Total Runs" value={String(history.length)} />
        <StatCard label="Critic Rejections" value={String(criticRejections)} tone={criticRejections ? "warn" : "good"} />
        <StatCard label="Contradictions Flagged" value={String(contradictions)} tone={contradictions ? "bad" : "good"} />
        <StatCard label="Security Checks Passed" value={`${Math.round(securityPassRate * 100)}%`} tone={securityPassRate === 1 ? "good" : "bad"} />
      </div>

      <div className="dash-grid">
        <div className="panel">
          <h2>Confidence Over Time{technical && <span className="tech-caption"> · last {chronological.length} runs</span>}</h2>
          {confidenceSeries.length >= 2 ? (
            <Sparkline points={confidenceSeries} width={480} height={90} />
          ) : (
            <div className="empty">Run a few checks to see a trend.</div>
          )}
        </div>

        <div className="panel">
          <h2>Decision Distribution</h2>
          <BarMini
            items={[
              { label: "Auto-Optimize", value: counts.AUTO_OPTIMIZE, color: "var(--green)" },
              { label: "Insufficient Data", value: counts.INSUFFICIENT_DATA, color: "var(--amber)" },
              { label: "Critical Halt", value: counts.CRITICAL_HALT, color: "var(--red)" },
            ]}
          />
        </div>
      </div>

      <div className="panel">
        <h2>System Health</h2>
        <div className="gauge-row">
          <Donut value={avgConfidence} color="var(--accent)" sub="Avg. confidence" />
          <Donut value={counts.AUTO_OPTIMIZE / total} color="var(--green)" sub="Healthy decisions" />
          <Donut value={1 - criticRejections / total} color="var(--amber)" sub="Critic validity" />
          <Donut value={securityPassRate} color="var(--green)" sub="Security integrity" />
        </div>
      </div>
    </div>
  );
}
