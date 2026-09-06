// Every "break something on purpose" button maps to a real, countable outcome
// in the audit trail / decision history — this tallies how many times each
// injected failure was actually caught, instead of a hardcoded pass/fail.
import { useFleet } from "../FleetDataContext";
import { BarMini } from "../charts";

export function FailureInjectionCard() {
  const { history, audit } = useFleet();

  const probes = audit.filter((r) => r.event_type === "security_probe");
  const probesBlocked = probes.filter((r) => r.payload.blocked).length;
  const probesExposed = probes.length - probesBlocked;

  const corruptRejected = history.filter((d) => d.critic_rejected).length;
  const recoveredRetries = history.filter((d) => (d.trace.retries?.length ?? 0) > 0 && !d.critic_rejected).length;

  const items = [
    { label: "Corrupt Payloads Rejected", value: corruptRejected, color: "var(--emerald)" },
    { label: "Security Probes Blocked", value: probesBlocked, color: "var(--emerald)" },
    { label: "Transient Errors Recovered", value: recoveredRetries, color: "var(--emerald)" },
    ...(probesExposed > 0 ? [{ label: "Security Probes Exposed", value: probesExposed, color: "var(--rose)" }] : []),
  ];

  const anyData = items.some((i) => i.value > 0);

  return (
    <div className="panel">
      <h2>Failure Injection Success</h2>
      {!anyData ? (
        <div className="empty">Break something in Simulation Lab to see how the harness caught it.</div>
      ) : (
        <BarMini items={items} />
      )}
    </div>
  );
}
