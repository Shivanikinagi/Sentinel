import { useFleet } from "../FleetDataContext";
import { Donut } from "../charts";

export function HarnessTrustScoreCard() {
  const { decision } = useFleet();

  if (!decision) return null;

  const trustedCount = decision.trace.evidence_snapshot.filter((e) => e.status === "fresh").length;
  const totalCount = decision.trace.evidence_snapshot.length || 1;
  const freshnessScore = trustedCount / totalCount;

  const agentAvailScore =
    (decision.trace.agents_reporting.length /
      (decision.trace.agents_reporting.length + decision.trace.agents_unavailable.length || 1));

  const schemaScore = decision.critic_rejected ? 0.0 : 1.0;
  const verifierScore = decision.trace.verifier_result?.valid ? 1.0 : 0.5;

  const overallScore = Math.round(
    (freshnessScore * 0.3 + agentAvailScore * 0.3 + schemaScore * 0.2 + verifierScore * 0.2) * 100
  );

  const color =
    overallScore >= 85
      ? "var(--emerald)"
      : overallScore >= 60
      ? "var(--amber)"
      : "var(--rose)";

  return (
    <div className="trust-score-card">
      <div className="trust-score-header">
        <div>
          <span className="badge badge-info">HARNESS METRIC</span>
          <h3>Harness Trust Score™</h3>
          <p>Single executive metric quantifying real-time decision reliability</p>
        </div>
        <Donut value={overallScore / 100} size={84} stroke={9} color={color} label={`${overallScore}%`} sub="TRUST" />
      </div>

      <div className="trust-breakdown">
        <div className="trust-metric">
          <span className="metric-label">Freshness</span>
          <span className="metric-val font-mono">{Math.round(freshnessScore * 100)}%</span>
        </div>
        <div className="trust-metric">
          <span className="metric-label">Agent Health</span>
          <span className="metric-val font-mono">{Math.round(agentAvailScore * 100)}%</span>
        </div>
        <div className="trust-metric">
          <span className="metric-label">Schema Validity</span>
          <span className="metric-val font-mono">{Math.round(schemaScore * 100)}%</span>
        </div>
        <div className="trust-metric">
          <span className="metric-label">Verifier Checks</span>
          <span className="metric-val font-mono">{Math.round(verifierScore * 100)}%</span>
        </div>
      </div>
    </div>
  );
}
