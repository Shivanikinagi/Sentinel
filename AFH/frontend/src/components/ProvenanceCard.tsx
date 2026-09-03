import { useFleet } from "../FleetDataContext";

export function ProvenanceCard() {
  const { decision } = useFleet();
  const snapshot = decision?.trace?.evidence_snapshot ?? [];

  if (!decision || snapshot.length === 0) return null;

  return (
    <div className="provenance-card">
      <div className="provenance-header">
        <h3>🔍 Evidence Provenance & Cryptographic Auditing</h3>
        <span className="badge badge-info">{snapshot.length} Observations Verified</span>
      </div>

      <div className="provenance-grid">
        {snapshot.map((ev) => (
          <div key={ev.evidence_id} className="provenance-item">
            <div className="prov-top">
              <span className="prov-signal">{ev.signal}</span>
              <span className="prov-source font-mono">{ev.source}</span>
            </div>
            <div className="prov-value">
              {ev.value} {ev.unit}
            </div>
            {ev.provenance && (
              <div className="prov-meta font-mono">
                <div>Sensor: <strong>{ev.provenance.sensor_id}</strong></div>
                <div>Hash: <strong title={ev.provenance.raw_payload_hash}>{ev.provenance.raw_payload_hash}</strong></div>
                <div>Transforms: {ev.provenance.transformations.join(", ")}</div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
