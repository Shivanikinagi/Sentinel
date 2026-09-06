import { IsolationDemoCard } from "../components/IsolationDemoCard";

export default function IsolationDemo() {
  return (
    <div className="page">
      <div className="panel">
        <h2>Agent Isolation</h2>
        <p className="stat-sub" style={{ marginBottom: 0 }}>
          The Vehicle Agent has no callable path to the Environment Agent's tools —
          not a permission check, a missing reference entirely.
        </p>
      </div>
      <IsolationDemoCard />
    </div>
  );
}
