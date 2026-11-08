import { useState } from "react";
import { Sun, Moon, MonitorCog, Shield, AlertTriangle, LogOut, Info, Trash2 } from "lucide-react";
import { useAuth } from "@/lib/auth/AuthContext";
import { useTheme } from "@/hooks/useTheme";
import { sessionsApi } from "@/lib/api/sessions";
import { ConfirmDialog } from "@/components/layout/ConfirmDialog";

interface SettingsViewProps {
  onNavigate?: (path: string) => void;
}

export function SettingsView({ onNavigate }: SettingsViewProps) {
  const { user, signOut } = useAuth();
  const { theme, setTheme } = useTheme();
  const [showClearConfirm, setShowClearConfirm] = useState(false);
  const [isClearing, setIsClearing] = useState(false);
  const [actionNotice, setActionNotice] = useState<string | null>(null);

  const handleClearAllSessions = async () => {
    setIsClearing(true);
    try {
      const sessions = await sessionsApi.list();
      await Promise.all(sessions.map((s) => sessionsApi.remove(s.id)));
      setActionNotice("All conversations have been permanently removed.");
      setShowClearConfirm(false);
    } catch {
      setActionNotice("Failed to clear some conversations. Please refresh.");
    } finally {
      setIsClearing(false);
    }
  };

  return (
    <div
      className="feature-page settings-page"
      style={{
        maxWidth: "760px",
        width: "100%",
        margin: "0 auto",
        padding: "32px 20px 48px",
        display: "flex",
        flexDirection: "column",
        gap: "28px",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div>
          <h1 style={{ margin: "0 0 4px", fontSize: "20px", fontWeight: 700, color: "var(--color-text-primary)" }}>
            Settings & System Information
          </h1>
          <p style={{ margin: 0, fontSize: "14px", color: "var(--color-text-secondary)" }}>
            Manage your account preferences, appearance, and view engine architecture specifications.
          </p>
        </div>
        {onNavigate && (
          <button
            type="button"
            onClick={() => onNavigate("home")}
            style={{
              padding: "6px 14px",
              borderRadius: "var(--radius-sm)",
              border: "1px solid var(--color-border-subtle)",
              background: "transparent",
              color: "var(--color-text-secondary)",
              fontSize: "13px",
              fontWeight: 500,
              cursor: "pointer",
            }}
          >
            Dashboard
          </button>
        )}
      </div>

      {actionNotice && (
        <div
          style={{
            padding: "10px 14px",
            borderRadius: "var(--radius-sm)",
            backgroundColor: "var(--color-accent-subtle)",
            border: "1px solid var(--color-accent-border)",
            color: "var(--color-accent)",
            fontSize: "13px",
            fontWeight: 500,
          }}
        >
          {actionNotice}
        </div>
      )}

      {/* 1. Appearance / Theme */}
      <section className="settings-panel"
        style={{
          display: "flex",
          flexDirection: "column",
          gap: "14px",
          backgroundColor: "var(--color-surface)",
          border: "1px solid var(--color-border-subtle)",
          borderRadius: "var(--radius-md)",
          padding: "20px",
        }}
      >
        <h2 style={{ margin: 0, fontSize: "14px", fontWeight: 600, color: "var(--color-text-primary)" }}>
          Appearance & Theme
        </h2>
        <div style={{ display: "flex", gap: "8px" }}>
          <button
            type="button"
            onClick={() => setTheme("light")}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              padding: "8px 14px",
              borderRadius: "var(--radius-sm)",
              border: `1px solid ${theme === "light" ? "var(--color-accent)" : "var(--color-border-subtle)"}`,
              backgroundColor: theme === "light" ? "var(--color-accent-subtle)" : "var(--color-canvas)",
              color: theme === "light" ? "var(--color-accent)" : "var(--color-text-secondary)",
              fontSize: "13px",
              fontWeight: 500,
              cursor: "pointer",
            }}
          >
            <Sun size={15} />
            <span>Light</span>
          </button>

          <button
            type="button"
            onClick={() => setTheme("dark")}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              padding: "8px 14px",
              borderRadius: "var(--radius-sm)",
              border: `1px solid ${theme === "dark" ? "var(--color-accent)" : "var(--color-border-subtle)"}`,
              backgroundColor: theme === "dark" ? "var(--color-accent-subtle)" : "var(--color-canvas)",
              color: theme === "dark" ? "var(--color-accent)" : "var(--color-text-secondary)",
              fontSize: "13px",
              fontWeight: 500,
              cursor: "pointer",
            }}
          >
            <Moon size={15} />
            <span>Dark</span>
          </button>

          <button
            type="button"
            onClick={() => setTheme("system")}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              padding: "8px 14px",
              borderRadius: "var(--radius-sm)",
              border: `1px solid ${theme === "system" ? "var(--color-accent)" : "var(--color-border-subtle)"}`,
              backgroundColor: theme === "system" ? "var(--color-accent-subtle)" : "var(--color-canvas)",
              color: theme === "system" ? "var(--color-accent)" : "var(--color-text-secondary)",
              fontSize: "13px",
              fontWeight: 500,
              cursor: "pointer",
            }}
          >
            <MonitorCog size={15} />
            <span>System Default</span>
          </button>
        </div>
      </section>

      {/* 2. Account Profile */}
      <section className="settings-panel"
        style={{
          display: "flex",
          flexDirection: "column",
          gap: "14px",
          backgroundColor: "var(--color-surface)",
          border: "1px solid var(--color-border-subtle)",
          borderRadius: "var(--radius-md)",
          padding: "20px",
        }}
      >
        <h2 style={{ margin: 0, fontSize: "14px", fontWeight: 600, color: "var(--color-text-primary)" }}>
          User Account Profile
        </h2>

        <div style={{ display: "flex", flexDirection: "column", gap: "10px", fontSize: "13px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid var(--color-border-subtle)" }}>
            <span style={{ color: "var(--color-text-tertiary)" }}>Email Address</span>
            <strong style={{ color: "var(--color-text-primary)" }}>{user?.email ?? "Not authenticated"}</strong>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid var(--color-border-subtle)" }}>
            <span style={{ color: "var(--color-text-tertiary)" }}>Authentication Mode</span>
            <span style={{ color: "var(--color-text-primary)", fontWeight: 500 }}>JWT Dual Token (Access + Refresh)</span>
          </div>
        </div>

        <div style={{ display: "flex", justifyContent: "flex-end", marginTop: "6px" }}>
          <button
            type="button"
            onClick={() => void signOut()}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "6px",
              padding: "7px 14px",
              borderRadius: "var(--radius-sm)",
              border: "1px solid var(--color-status-error)",
              backgroundColor: "transparent",
              color: "var(--color-status-error)",
              fontSize: "13px",
              fontWeight: 500,
              cursor: "pointer",
            }}
          >
            <LogOut size={14} />
            <span>Sign Out</span>
          </button>
        </div>
      </section>

      {/* 3. Session Management & Privacy */}
      <section className="settings-panel"
        style={{
          display: "flex",
          flexDirection: "column",
          gap: "14px",
          backgroundColor: "var(--color-surface)",
          border: "1px solid var(--color-border-subtle)",
          borderRadius: "var(--radius-md)",
          padding: "20px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <Shield size={16} style={{ color: "var(--color-accent)" }} />
          <h2 style={{ margin: 0, fontSize: "14px", fontWeight: 600, color: "var(--color-text-primary)" }}>
            Conversation Data & Privacy
          </h2>
        </div>
        <p style={{ margin: 0, fontSize: "13px", color: "var(--color-text-secondary)", lineHeight: 1.5 }}>
          Your conversation sessions and diagnostic analyses are stored securely in PostgreSQL with thread-level isolation.
          You can delete individual conversations from the sidebar or clear all sessions at once.
        </p>

        <div style={{ display: "flex", justifyContent: "flex-end" }}>
          <button
            type="button"
            onClick={() => setShowClearConfirm(true)}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "6px",
              padding: "7px 14px",
              borderRadius: "var(--radius-sm)",
              border: "1px solid var(--color-border-strong)",
              backgroundColor: "var(--color-canvas)",
              color: "var(--color-status-error)",
              fontSize: "13px",
              fontWeight: 500,
              cursor: "pointer",
            }}
          >
            <Trash2 size={14} />
            <span>Clear All Conversations</span>
          </button>
        </div>
      </section>

      {/* 4. Engine Architecture & Disclaimers */}
      <section className="settings-panel"
        style={{
          display: "flex",
          flexDirection: "column",
          gap: "14px",
          backgroundColor: "var(--color-sunken)",
          border: "1px solid var(--color-border-subtle)",
          borderRadius: "var(--radius-md)",
          padding: "20px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <Info size={16} style={{ color: "var(--color-text-secondary)" }} />
          <h2 style={{ margin: 0, fontSize: "14px", fontWeight: 600, color: "var(--color-text-primary)" }}>
            Integrated Engine Specifications
          </h2>
        </div>

        <ul style={{ margin: 0, paddingLeft: "18px", fontSize: "12px", color: "var(--color-text-secondary)", lineHeight: 1.6 }}>
          <li>
            <strong>Crop Recommendation:</strong> Scikit-Learn Random Forest Classifier trained on 2,200 multi-regional agricultural records across 22 crop classes.
          </li>
          <li>
            <strong>Plant Disease Detection:</strong> MobileNet-V2 PlantVillage vision model evaluating 38 distinct crop-pathogen classes (14 crop varieties).
          </li>
          <li>
            <strong>Supervisor Routing:</strong> LangGraph state graph enforcing 7-parameter input completeness for crop predictions and isolating fertilizer advisories to the General Agent.
          </li>
          <li>
            <strong>RAG Vector Store:</strong> Qdrant vector database indexing verified ICAR package of practices and plant pathology management sheets.
          </li>
        </ul>

        <div
          style={{
            display: "flex",
            alignItems: "flex-start",
            gap: "8px",
            padding: "10px 12px",
            borderRadius: "var(--radius-sm)",
            backgroundColor: "var(--color-surface)",
            border: "1px solid var(--color-border-subtle)",
            fontSize: "11px",
            color: "var(--color-text-secondary)",
            lineHeight: 1.5,
          }}
        >
          <AlertTriangle size={15} style={{ color: "var(--color-status-warning)", flexShrink: 0, marginTop: "1px" }} />
          <span>
            <strong>Mandatory Agronomic Disclaimer:</strong> All recommendations are generated by machine learning models and factual reference retrieval. Do not apply concentrated synthetic fertilizers or chemical fungicides without local soil test reports and consultation with a local agricultural extension officer (KVK).
          </span>
        </div>
      </section>

      {/* Confirm Clear Modal Dialog */}
      <ConfirmDialog
        isOpen={showClearConfirm}
        title="Clear All Conversations?"
        message="This action will permanently delete all your conversation history and diagnostic sessions from the database. This action cannot be undone."
        confirmLabel={isClearing ? "Clearing…" : "Delete All"}
        cancelLabel="Cancel"
        isDestructive={true}
        onConfirm={handleClearAllSessions}
        onCancel={() => setShowClearConfirm(false)}
      />
    </div>
  );
}
