import { PanelLeft, Settings } from "lucide-react";
import { useAuth } from "@/lib/auth/AuthContext";
import type { AppRoute } from "@/hooks/useHashRoute";

interface AppHeaderProps {
  currentRoute: AppRoute;
  sessionTitle?: string;
  sidebarCollapsed: boolean;
  onToggleSidebar: () => void;
  onNavigate: (route: string) => void;
}

export function AppHeader({ currentRoute, sessionTitle, sidebarCollapsed, onToggleSidebar, onNavigate }: AppHeaderProps) {
  const { user } = useAuth();

  const getRouteTitle = () => {
    switch (currentRoute) {
      case "home":
        return "Dashboard";
      case "crop":
        return "Crop Recommendation";
      case "disease":
        return "Plant Disease Diagnosis";
      case "settings":
        return "System Settings";
      case "chat":
        return sessionTitle || "Field Consultation";
      default:
        return "Dashboard";
    }
  };

  return (
    <header
      className="app-header"
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        height: "56px",
        padding: "0 20px",
        borderBottom: "1px solid var(--color-border-subtle)",
        backgroundColor: "var(--color-surface)",
        flexShrink: 0,
        zIndex: 10,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "12px", minWidth: 0 }}>
        <button
          type="button"
          onClick={onToggleSidebar}
          aria-label={sidebarCollapsed ? "Show sidebar" : "Hide sidebar"}
          style={{
            display: "none", // Visible on tablet/mobile via CSS
            padding: "6px",
            border: "1px solid var(--color-border-subtle)",
            borderRadius: "var(--radius-sm)",
            background: "transparent",
            color: "var(--color-text-secondary)",
            cursor: "pointer",
          }}
          className="header-mobile-toggle"
        >
          <PanelLeft size={18} />
        </button>

        <div style={{ display: "flex", alignItems: "center", gap: "8px", minWidth: 0 }}>
          <span
            style={{
              fontSize: "12px",
              fontWeight: 600,
              textTransform: "uppercase",
              letterSpacing: "0.08em",
              color: "var(--color-text-tertiary)",
            }}
          >
            CropSage
          </span>
          <span style={{ color: "var(--color-border-strong)", fontSize: "14px" }}>/</span>
          <h1
            style={{
              margin: 0,
              fontSize: "14px",
              fontWeight: 600,
              color: "var(--color-text-primary)",
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            {getRouteTitle()}
          </h1>
        </div>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
        {/* Settings button */}
        <button
          type="button"
          onClick={() => onNavigate("settings")}
          aria-label="Settings"
          title="Settings"
          style={{
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            width: "32px",
            height: "32px",
            borderRadius: "var(--radius-sm)",
            border: "1px solid var(--color-border-subtle)",
            background: currentRoute === "settings" ? "var(--color-surface-hover)" : "transparent",
            color: currentRoute === "settings" ? "var(--color-text-primary)" : "var(--color-text-secondary)",
            cursor: "pointer",
          }}
        >
          <Settings size={15} />
        </button>

        {/* User initials */}
        {user?.email && (
          <div
            title={`Signed in as ${user.email}`}
            style={{
              display: "grid",
              placeItems: "center",
              width: "30px",
              height: "30px",
              borderRadius: "var(--radius-sm)",
              backgroundColor: "var(--color-accent-subtle)",
              color: "var(--color-accent)",
              fontSize: "12px",
              fontWeight: 600,
              cursor: "pointer",
            }}
            onClick={() => onNavigate("settings")}
          >
            {user.email.slice(0, 2).toUpperCase()}
          </div>
        )}
      </div>
    </header>
  );
}

