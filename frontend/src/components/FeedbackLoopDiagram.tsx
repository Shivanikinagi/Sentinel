// The mechanism, drawn as a diagram instead of a checklist: two agents
// converge on trusted evidence, the Risk Assessment Engine reasons over it,
// the Verifier grounds that reasoning against the same evidence, and a
// failure doesn't dead-end — it feeds back to the Risk Assessment Engine for
// one bounded reassessment before the Decision Authority ever sees it. The
// top half (agents → evidence → reasoning → verification) is always true;
// only the PASS/FAIL fork and feedback path reflect this run's real outcome.
import { useFleet } from "../FleetDataContext";

type Tone = "neutral" | "active" | "good" | "bad";

function Box({
  x, y, w, h = 40, label, sub, tone,
}: { x: number; y: number; w: number; h?: number; label: string; sub?: string; tone: Tone }) {
  return (
    <g>
      <rect x={x} y={y} width={w} height={h} rx={8} className={`fld-box fld-${tone}`} />
      <text x={x + w / 2} y={y + h / 2 - (sub ? 6 : 0)} textAnchor="middle" dominantBaseline="middle" className="fld-label">
        {label}
      </text>
      {sub && (
        <text x={x + w / 2} y={y + h / 2 + 12} textAnchor="middle" className="fld-sub">
          {sub}
        </text>
      )}
    </g>
  );
}

function Arrow({ x1, y1, x2, y2, tone = "" }: { x1: number; y1: number; x2: number; y2: number; tone?: string }) {
  return <line x1={x1} y1={y1} x2={x2} y2={y2} className={`fld-arrow ${tone}`} markerEnd="url(#fld-arrowhead)" />;
}

export function FeedbackLoopDiagram() {
  const { decision } = useFleet();
  const valid = decision?.trace.verifier_result?.valid ?? null;
  const looped = decision?.trace.feedback_loop_triggered ?? false;
  const passed = valid === true;
  const failedFinal = valid === false;

  return (
    <div className="panel">
      <h2>Agent → Critic → Verifier Feedback Loop</h2>
      <svg viewBox="0 0 620 340" className="feedback-loop-svg">
        <defs>
          <marker id="fld-arrowhead" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
            <path d="M0,0 L8,4 L0,8 Z" className="fld-arrowhead" />
          </marker>
        </defs>

        <Box x={20} y={10} w={190} label="Vehicle Agent" tone="active" />
        <Box x={230} y={10} w={190} label="Environment Agent" tone="active" />
        <Arrow x1={115} y1={50} x2={200} y2={78} />
        <Arrow x1={325} y1={50} x2={250} y2={78} />

        <Box x={135} y={78} w={220} label="Trusted Evidence" tone="active" />
        <Arrow x1={245} y1={118} x2={245} y2={146} />

        <Box x={135} y={146} w={220} label="Risk Assessment Engine" sub="LLM · advisory only" tone={looped ? "active" : "active"} />
        <Arrow x1={245} y1={186} x2={245} y2={214} />

        <Box x={135} y={214} w={220} label="Verifier" sub="grounds every factor in evidence" tone={looped ? "bad" : "active"} />

        <Arrow x1={210} y1={254} x2={110} y2={288} tone={passed ? "fld-good" : ""} />
        <Arrow x1={280} y1={254} x2={470} y2={288} tone={failedFinal || looped ? "fld-bad" : ""} />

        <Box x={20} y={288} w={180} label="PASS" sub="→ Decision Authority" tone={passed ? "good" : "neutral"} />
        <Box x={390} y={288} w={170} label="FAIL" sub="Verifier rejects" tone={looped || failedFinal ? "bad" : "neutral"} />

        <path
          d="M 470 288 C 580 200, 580 110, 360 160"
          fill="none"
          className={`fld-arrow fld-feedback${looped ? " fld-active" : ""}`}
          markerEnd="url(#fld-arrowhead)"
        />
        <text x="560" y="230" textAnchor="middle" className="fld-feedback-label">feedback</text>
      </svg>
      <div className="panel-sub">
        {looped
          ? "This run: the Verifier rejected the first pass, fed its reason back, the Critic revised, the Verifier re-checked and passed."
          : passed
          ? "This run: the Verifier passed the first pass — no feedback needed."
          : failedFinal
          ? "This run: the Verifier rejected even after feedback — Decision Authority falls back to INSUFFICIENT_DATA, not a guess."
          : "Run the harness to see this run's actual path highlighted."}
      </div>
    </div>
  );
}
