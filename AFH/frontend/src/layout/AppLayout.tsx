import { useState } from "react";
import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";
import { PresenterGuide } from "../components/PresenterGuide";

export function AppLayout() {
  const [guideOpen, setGuideOpen] = useState(false);

  return (
    <div className="shell">
      <Sidebar />
      <div className="shell-main">
        <Topbar onOpenGuide={() => setGuideOpen(true)} />
        <main className="shell-content">
          <Outlet />
        </main>
      </div>
      <PresenterGuide isOpen={guideOpen} onClose={() => setGuideOpen(false)} />
    </div>
  );
}
