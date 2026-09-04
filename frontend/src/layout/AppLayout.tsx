import { useState } from "react";
import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";
import { PresenterGuide } from "../components/PresenterGuide";
import { DecisionExplainerModal } from "../components/DecisionExplainerModal";

export function AppLayout() {
  const [guideOpen, setGuideOpen] = useState(false);
  const [explainerOpen, setExplainerOpen] = useState(false);

  return (
    <div className="shell">
      <Sidebar />
      <div className="shell-main">
        <Topbar onOpenGuide={() => setGuideOpen(true)} onOpenExplainer={() => setExplainerOpen(true)} />
        <main className="shell-content">
          <Outlet />
        </main>
      </div>
      <PresenterGuide isOpen={guideOpen} onClose={() => setGuideOpen(false)} />
      <DecisionExplainerModal isOpen={explainerOpen} onClose={() => setExplainerOpen(false)} />
    </div>
  );
}
