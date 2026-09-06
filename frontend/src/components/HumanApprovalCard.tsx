// Shown only when the deterministic Controller halted automation — this is
// the one moment a human, not the AI, makes the call. Hidden entirely for
// AUTO_OPTIMIZE so it never competes with the good-news path.
import { useFleet } from "../FleetDataContext";
import { humanizeReason } from "../humanize";
import { CheckCircle, XCircle } from "../icons";

export function HumanApprovalCard() {
  const { decision, actions, approve, reject } = useFleet();
  if (decision?.controller_state !== "CRITICAL_HALT" || actions.length === 0) return null;

  return (
    <div className="human-approval-card">
      <div className="ha-header">
        <span className="status-pill tone-bad">Approval Pending</span>
        <span className="ha-count">
          {actions.length} decision{actions.length > 1 ? "s" : ""} require{actions.length > 1 ? "" : "s"} a human approval
        </span>
      </div>
      {actions.map((a) => (
        <div className="ha-row" key={a.action_id}>
          <div className="ha-reason">
            <span className="ha-reason-label">Reason</span>
            {humanizeReason(a.reason)}
          </div>
          <div className="ha-btns">
            <button className="ok" onClick={() => approve(a.action_id)}><CheckCircle size={14} /> Approve</button>
            <button className="danger" onClick={() => reject(a.action_id)}><XCircle size={14} /> Reject</button>
          </div>
        </div>
      ))}
    </div>
  );
}
