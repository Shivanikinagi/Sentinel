// Estimated LLM spend for the run — the mock backend never talks to a real
// model, so there's no metered usage to read. Instead of inventing a number,
// this estimates token counts from the ACTUAL payload the Risk Assessment
// Engine builds for this run (the same evidence list + system prompt shape
// critic.py sends), using the standard ~4-chars-per-token approximation.
// Labeled "Estimated" throughout so it never reads as a metered figure.
import { useFleet } from "../FleetDataContext";

const SYSTEM_PROMPT_CHARS = 620; // length of critic.py's fixed system prompt
const PRICE_PER_1K_PROMPT = 0.00015;
const PRICE_PER_1K_COMPLETION = 0.0006;

function estimateTokens(chars: number): number {
  return Math.max(1, Math.round(chars / 4));
}

export function TokenUsageCard() {
  const { decision } = useFleet();

  if (!decision) {
    return (
      <div className="panel">
        <h2>Token Usage <span className="tech-caption">· estimated</span></h2>
        <div className="empty">Run the harness to see estimated token usage.</div>
      </div>
    );
  }

  const trusted = decision.trace.evidence_snapshot.filter(
    (e) => !decision.trace.excluded_evidence_ids.includes(e.evidence_id)
  );
  const evidencePayload = JSON.stringify(
    trusted.map((e) => ({ signal: e.signal, value: e.value, unit: e.unit, source: e.source, status: e.status }))
  );
  const promptTokens = estimateTokens(SYSTEM_PROMPT_CHARS + evidencePayload.length);

  const rm = decision.risk_matrix;
  const completionChars = rm
    ? JSON.stringify(rm).length
    : (decision.trace.verifier_result ? JSON.stringify(decision.trace.verifier_result).length : 40);
  const completionTokens = estimateTokens(completionChars);

  const cost = (promptTokens / 1000) * PRICE_PER_1K_PROMPT + (completionTokens / 1000) * PRICE_PER_1K_COMPLETION;

  return (
    <div className="panel">
      <h2>Token Usage <span className="tech-caption">· estimated</span></h2>
      <div className="token-usage-grid">
        <div className="token-usage-cell">
          <div className="exec-time-label">Prompt</div>
          <div className="exec-time-value">{promptTokens}</div>
        </div>
        <div className="token-usage-cell">
          <div className="exec-time-label">Completion</div>
          <div className="exec-time-value">{completionTokens}</div>
        </div>
        <div className="token-usage-cell">
          <div className="exec-time-label">Cost</div>
          <div className="exec-time-value">${cost.toFixed(4)}</div>
        </div>
      </div>
    </div>
  );
}
