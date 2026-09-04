import { useFleet } from "../FleetDataContext";

interface PresenterGuideProps {
  isOpen: boolean;
  onClose: () => void;
}

export function PresenterGuide({ isOpen, onClose }: PresenterGuideProps) {
  const fleet = useFleet();

  if (!isOpen) return null;

  const scenes = [
    {
      id: "healthy",
      title: "Scene 1: Healthy Operations",
      state: "AUTO_OPTIMIZE (100% Confidence)",
      badgeClass: "badge-success",
      trigger: () => fleet.setScenario("healthy"),
      story: "All telematics (cargo temp, ambient temp, cooling unit, dwell time) are fresh, valid, and physically consistent.",
      script: "Notice how all evidence passes the Trust Gate. The Critic LLM confirms risk is LOW. The deterministic controller awards 100% confidence and grants AUTO_OPTIMIZE authority.",
      proof: "gate.py (freshness) + confidence.py (100% math in code, never LLM)",
    },
    {
      id: "compound_risk",
      title: "Scene 2: Contradiction & Physical Anomaly",
      state: "CRITICAL_HALT (100% Confidence)",
      badgeClass: "badge-danger",
      trigger: () => fleet.setScenario("compound_risk"),
      story: "Cooling status reports ON (1.0), but cargo temperature is rising at 11.5°C in 41°C ambient weather.",
      script: "Here is the key contradiction! The LLM Critic notices that reporting cooling ON while cargo climbs is physically inconsistent. It flags a contradiction. The controller drops state to CRITICAL_HALT and requires HUMAN approval before any automated cooling override can execute.",
      proof: "critic.py (OpenRouter JSON validation) + verifier.py (3-point verification check) + actions.py (Layer 2 Action Gateway)",
    },
    {
      id: "sensor_blackout",
      title: "Scene 3: Agent / Sensor Blackout",
      state: "INSUFFICIENT_DATA (0% Confidence)",
      badgeClass: "badge-warning",
      trigger: () => fleet.killAgent("agent_a", true),
      story: "Agent A (truck telematics) loses network connection or crashes mid-route.",
      script: "If a sensor agent dies or goes offline, the harness does NOT hallucinate or guess. The Trust Gate flags missing required signals, reducing confidence to 0% and safely falling back to INSUFFICIENT_DATA.",
      proof: "test_isolation.py & gate.py (signal completeness enforcement)",
    },
    {
      id: "corrupt_llm",
      title: "Scene 4: Corrupt / Malformed LLM Output",
      state: "Schema Rejection -> INSUFFICIENT_DATA",
      badgeClass: "badge-purple",
      trigger: () => fleet.corruptLlm(),
      story: "Model returns invalid JSON, missing required fields, or extra hallucinated authority parameters.",
      script: "No LLM output reaches the Controller without strict Pydantic validation (extra='forbid') and Verifier self-consistency checks. Watch how a corrupted LLM response is instantly rejected, causing the harness to maintain safety rather than crashing.",
      proof: "critic.py (RiskMatrix validation) & verifier.py",
    },
    {
      id: "stale_signal",
      title: "Scene 5: Stale Telematics Data",
      state: "Trust Gate Filtering -> INSUFFICIENT_DATA",
      badgeClass: "badge-warning",
      trigger: () => fleet.staleSignal("cargo_temperature"),
      story: "Telematics telemetry is backdated by >300 seconds (e.g. replay attack or stale buffer).",
      script: "Even if an agent sends data, the Trust Gate checks timestamp provenance. Data older than the threshold is marked STALE/INVALID and discarded before reaching the LLM.",
      proof: "gate.py (timestamp window filtering)",
    },
    {
      id: "security_probe",
      title: "Scene 6: Agent Authority Red-Team Probe",
      state: "Security Enforcement Proven",
      badgeClass: "badge-info",
      trigger: () => fleet.runProbe(),
      story: "Simulates an adversarial agent trying to execute a fleet action directly.",
      script: "Notice that agents have no code paths to execute fleet actions. The Action Gateway is strictly protected by the Layer 2 Controller.",
      proof: "security.py & test_isolation.py & tools.py",
    },
  ];

  return (
    <div className="presenter-drawer-overlay" onClick={onClose}>
      <div className="presenter-drawer" onClick={(e) => e.stopPropagation()}>
        <div className="presenter-drawer-header">
          <div>
            <span className="presenter-tag">DEMO PRESENTER GUIDE</span>
            <h2>Judge Presentation Script & Pitch Quotes</h2>
            <p>Executive pitch lines and step-by-step scene walkthrough</p>
          </div>
          <button className="btn-close" onClick={onClose}>✕</button>
        </div>

        <div className="presenter-drawer-body">
          <div className="presenter-intro">
            <h4>🎤 Key Pitch Lines to Quote to Judges:</h4>
            <blockquote>
              <p>• "We don't just validate the LLM's output once—<strong>we verify it with our deterministic Verifier sub-system</strong>."</p>
              <p>• "Every decision has a <strong>cryptographic provenance trail</strong> and step-by-step trace timeline you can inspect."</p>
              <p>• "If the LLM fails or times out, the system doesn't crash—<strong>the Circuit Breaker trips and it degrades gracefully</strong>."</p>
              <p>• "The AI suggests; we decide; <strong>the deterministic code acts</strong>."</p>
              <p>• "This isn't about making AI perfect. It's about <strong>making the system reliable even when AI isn't</strong>."</p>
            </blockquote>
          </div>

          <div className="scenes-list">
            {scenes.map((scene, idx) => (
              <div key={scene.id} className="scene-card">
                <div className="scene-card-header">
                  <div>
                    <span className="scene-number">SCENE {idx + 1}</span>
                    <h3>{scene.title}</h3>
                  </div>
                  <span className={`badge ${scene.badgeClass}`}>{scene.state}</span>
                </div>

                <div className="scene-card-content">
                  <p className="scene-story"><strong>Scenario:</strong> {scene.story}</p>

                  <div className="scene-script">
                    <strong>🗣️ Presenter Script (Say this to judges):</strong>
                    <p>"{scene.script}"</p>
                  </div>

                  <div className="scene-proof">
                    <strong>🛡️ Harness Guarantee:</strong> <code>{scene.proof}</code>
                  </div>
                </div>

                <div className="scene-card-actions">
                  <button
                    className="btn btn-primary btn-sm"
                    onClick={() => {
                      scene.trigger();
                      onClose();
                    }}
                  >
                    ▶ Launch Scene {idx + 1}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="presenter-drawer-footer">
          <button className="btn btn-secondary" onClick={() => fleet.reset()}>
            🔄 Reset All Conditions
          </button>
          <button className="btn btn-primary" onClick={onClose}>
            Close Presenter Guide
          </button>
        </div>
      </div>
    </div>
  );
}
