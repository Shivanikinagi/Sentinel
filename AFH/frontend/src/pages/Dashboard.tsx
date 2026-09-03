import { useFleet } from "../FleetDataContext";
import { ControllerBanner, PendingActions } from "../components";
import { LiveExecutionPanel, LiveEventFeed, MissionControlAlert } from "../missioncontrol";

export default function Dashboard() {
  const {
    decision, history, world, actions, audit, technical, approve, reject, runNow, busy,
  } = useFleet();

  return (
    <div className="page">
      <div className="mc-topline">
        <div className="mc-topline-item">
          <span className="mc-topline-value">{actions.length}</span>
          <span className="mc-topline-label">Pending Decisions</span>
        </div>
        <span className="mc-topline-sep" />
        <div className="mc-topline-item">
          <span className="mc-topline-value">1</span>
          <span className="mc-topline-label">Vehicle Monitored</span>
        </div>
        <span className="mc-topline-sep" />
        <div className="mc-topline-item">
          <span className="mc-topline-value">{history.length}</span>
          <span className="mc-topline-label">Checks This Session</span>
        </div>
      </div>

      <MissionControlAlert actions={actions} />

      <div className="mission-control">
        <LiveExecutionPanel decision={decision} world={world} actions={actions} busy={busy} onRun={runNow} />
        <LiveEventFeed audit={audit} />
      </div>

      {decision && <ControllerBanner d={decision} technical={technical} />}
      <PendingActions actions={actions} onApprove={approve} onReject={reject} technical={technical} />
    </div>
  );
}
