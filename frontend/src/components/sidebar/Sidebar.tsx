import { LogOut, Moon, Sun, X, MonitorCog, LayoutDashboard, Wheat, Microscope, MessageSquare, Settings } from "lucide-react";
import { useAuth } from "@/lib/auth/AuthContext";
import { useTheme, type ThemeMode } from "@/hooks/useTheme";
import type { AppRoute } from "@/hooks/useHashRoute";
import { NewChatButton, ThreadList } from "./ThreadList";

interface SidebarProps {
  open: boolean;
  collapsed?: boolean;
  currentRoute?: AppRoute;
  onNavigate?: (route: AppRoute) => void;
  onClose: () => void;
}

export function Sidebar({ open, collapsed = false, currentRoute = "home", onNavigate, onClose }: SidebarProps) {
  const { user, signOut } = useAuth();
  const { theme, setTheme } = useTheme();

  const handleNav = (route: AppRoute) => {
    if (onNavigate) onNavigate(route);
    onClose();
  };

  return (
    <aside className={`app-sidebar ${open ? "open" : ""} ${collapsed ? "collapsed" : ""}`}>
      {/* Brand Header */}
      <div className="sidebar-brand">
        <span
          style={{
            width: "8px",
            height: "8px",
            borderRadius: "50%",
            backgroundColor: "var(--color-accent)",
            display: "inline-block",
            flexShrink: 0,
          }}
        />
        <span style={{ fontWeight: 700, fontSize: "16px", letterSpacing: "-0.02em" }}>CropSage</span>
        <button className="mobile-close" onClick={onClose} aria-label="Close sidebar">
          <X size={17} />
        </button>
      </div>

      {/* Primary Section Navigation */}
      <nav
        style={{
          display: "flex",
          flexDirection: "column",
          gap: "3px",
          padding: "14px 4px 10px",
          borderBottom: "1px solid var(--color-border-subtle)",
          marginBottom: "12px",
        }}
      >
        <button
          type="button"
          onClick={() => handleNav("home")}
          style={{
            display: "flex",
            alignItems: "center",
            gap: "10px",
            width: "100%",
            padding: "8px 10px",
            borderRadius: "var(--radius-sm)",
            border: "none",
            backgroundColor: currentRoute === "home" ? "var(--color-accent-subtle)" : "transparent",
            color: currentRoute === "home" ? "var(--color-accent)" : "var(--color-text-primary)",
            fontSize: "13px",
            fontWeight: currentRoute === "home" ? 600 : 500,
            cursor: "pointer",
            textAlign: "left",
          }}
        >
          <LayoutDashboard size={16} />
          <span>Dashboard</span>
        </button>

        <button
          type="button"
          onClick={() => handleNav("crop")}
          style={{
            display: "flex",
            alignItems: "center",
            gap: "10px",
            width: "100%",
            padding: "8px 10px",
            borderRadius: "var(--radius-sm)",
            border: "none",
            backgroundColor: currentRoute === "crop" ? "var(--color-accent-subtle)" : "transparent",
            color: currentRoute === "crop" ? "var(--color-accent)" : "var(--color-text-primary)",
            fontSize: "13px",
            fontWeight: currentRoute === "crop" ? 600 : 500,
            cursor: "pointer",
            textAlign: "left",
          }}
        >
          <Wheat size={16} />
          <span>Crop Recommendation</span>
        </button>

        <button
          type="button"
          onClick={() => handleNav("disease")}
          style={{
            display: "flex",
            alignItems: "center",
            gap: "10px",
            width: "100%",
            padding: "8px 10px",
            borderRadius: "var(--radius-sm)",
            border: "none",
            backgroundColor: currentRoute === "disease" ? "var(--color-accent-subtle)" : "transparent",
            color: currentRoute === "disease" ? "var(--color-accent)" : "var(--color-text-primary)",
            fontSize: "13px",
            fontWeight: currentRoute === "disease" ? 600 : 500,
            cursor: "pointer",
            textAlign: "left",
          }}
        >
          <Microscope size={16} />
          <span>Disease Diagnosis</span>
        </button>

        <button
          type="button"
          onClick={() => handleNav("chat")}
          style={{
            display: "flex",
            alignItems: "center",
            gap: "10px",
            width: "100%",
            padding: "8px 10px",
            borderRadius: "var(--radius-sm)",
            border: "none",
            backgroundColor: currentRoute === "chat" ? "var(--color-accent-subtle)" : "transparent",
            color: currentRoute === "chat" ? "var(--color-accent)" : "var(--color-text-primary)",
            fontSize: "13px",
            fontWeight: currentRoute === "chat" ? 600 : 500,
            cursor: "pointer",
            textAlign: "left",
          }}
        >
          <MessageSquare size={16} />
          <span>Chat Consultation</span>
        </button>

        <button
          type="button"
          onClick={() => handleNav("settings")}
          style={{
            display: "flex",
            alignItems: "center",
            gap: "10px",
            width: "100%",
            padding: "8px 10px",
            borderRadius: "var(--radius-sm)",
            border: "none",
            backgroundColor: currentRoute === "settings" ? "var(--color-accent-subtle)" : "transparent",
            color: currentRoute === "settings" ? "var(--color-accent)" : "var(--color-text-primary)",
            fontSize: "13px",
            fontWeight: currentRoute === "settings" ? 600 : 500,
            cursor: "pointer",
            textAlign: "left",
          }}
        >
          <Settings size={16} />
          <span>Settings</span>
        </button>
      </nav>

      {/* New Chat Button */}
      <div className="sidebar-action" style={{ padding: "0 4px 12px" }}>
        <NewChatButton onOpenChat={() => handleNav("chat")} />
      </div>

      {/* History Thread List */}
      <ThreadList onOpenChat={() => handleNav("chat")} />

      {/* Footer Strip */}
      <div className="sidebar-bottom">
        {currentRoute !== "settings" && (
          <div className="theme-strip" aria-label="Theme">
            <button
              className={theme === "light" ? "selected" : ""}
              onClick={() => setTheme("light")}
              aria-label="Light theme"
            >
              <Sun size={14} />
              <span>Light</span>
            </button>
            <button
              className={theme === "system" ? "selected" : ""}
              onClick={() => setTheme("system")}
              aria-label="System theme"
            >
              <MonitorCog size={14} />
              <span>System</span>
            </button>
            <button
              className={theme === "dark" ? "selected" : ""}
              onClick={() => setTheme("dark")}
              aria-label="Dark theme"
            >
              <Moon size={14} />
              <span>Dark</span>
            </button>
          </div>
        )}

        <div className="sidebar-user">
          <div className="user-avatar">{user?.email.slice(0, 1).toUpperCase()}</div>
          <div className="user-details">
            <strong>{user?.email.split("@")[0]}</strong>
            <span>{user?.email}</span>
          </div>
          <button className="logout-button" onClick={() => void signOut()} aria-label="Log out">
            <LogOut size={16} />
          </button>
        </div>
      </div>
    </aside>
  );
}

export function ThemeLabel({ mode }: { mode: ThemeMode }) {
  return <span>{mode === "light" ? "Light" : mode === "dark" ? "Dark" : "System"}</span>;
}
