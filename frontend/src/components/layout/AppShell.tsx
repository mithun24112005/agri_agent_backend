import { useState, type ReactNode } from "react";
import { Sidebar } from "@/components/sidebar/Sidebar";
import { AppHeader } from "./AppHeader";
import { useHashRoute, type AppRoute } from "@/hooks/useHashRoute";

interface AppShellProps {
  children?: ReactNode;
  activeSessionTitle?: string;
  renderView: (route: AppRoute, navigate: (path: string) => void) => ReactNode;
}

export function AppShell({ activeSessionTitle, renderView }: AppShellProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const { route, navigate } = useHashRoute();

  const toggleSidebar = () => {
    if (window.matchMedia("(max-width: 850px)").matches) {
      setSidebarOpen(true);
      return;
    }
    setSidebarCollapsed((previous) => !previous);
  };

  return (
    <div className={`app-shell ${sidebarCollapsed ? "sidebar-collapsed" : ""}`} style={{ display: "flex", width: "100%", height: "100vh", overflow: "hidden" }}>
      {/* Mobile backdrop scrim */}
      <div
        className={`mobile-scrim ${sidebarOpen ? "open" : ""}`}
        onClick={() => setSidebarOpen(false)}
        aria-hidden={!sidebarOpen}
      />

      {/* Sidebar with route navigation */}
      <Sidebar
        open={sidebarOpen}
        collapsed={sidebarCollapsed}
        currentRoute={route}
        onNavigate={(newRoute) => {
          navigate(newRoute);
          setSidebarOpen(false);
        }}
        onClose={() => setSidebarOpen(false)}
      />

      {/* Main content frame with responsive header */}
      <div
        className="app-main-frame"
        style={{
          display: "flex",
          flexDirection: "column",
          flex: 1,
          minWidth: 0,
          height: "100vh",
          overflow: "hidden",
          backgroundColor: "var(--color-canvas)",
        }}
      >
        <AppHeader
          currentRoute={route}
          sessionTitle={activeSessionTitle}
          sidebarCollapsed={sidebarCollapsed}
          onToggleSidebar={toggleSidebar}
          onNavigate={(target) => navigate(target)}
        />

        <main
          style={{
            flex: 1,
            minHeight: 0,
            overflowY: "auto",
            display: "flex",
            flexDirection: "column",
          }}
        >
          {renderView(route, navigate)}
        </main>
      </div>
    </div>
  );
}

