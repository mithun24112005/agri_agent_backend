import { useAuiState } from "@assistant-ui/react";
import { AgriThread } from "@/components/assistant-ui/Thread";

export function ChatWorkspace() {
  const activeTitle = useAuiState(
    (state) =>
      state.threads.threadItems.find((item) => item.id === state.threads.mainThreadId)?.title ??
      "New conversation"
  );

  return (
    <section className="chat-workspace" style={{ flex: 1, display: "flex", flexDirection: "column", minHeight: 0 }}>
      {/* Sub-bar for conversation title and session state */}
      <div
        className="conversation-topbar"
        style={{
          display: "flex",
          alignItems: "center",
          gap: "8px",
          padding: "10px 24px",
          borderBottom: "1px solid var(--color-border-subtle)",
          backgroundColor: "var(--color-surface)",
          fontSize: "13px",
          color: "var(--color-text-secondary)",
          flexShrink: 0,
        }}
      >
        <span
          style={{
            width: "6px",
            height: "6px",
            borderRadius: "50%",
            backgroundColor: "var(--color-accent)",
          }}
        />
        <span style={{ fontWeight: 500, color: "var(--color-text-primary)" }}>{activeTitle}</span>
        <span style={{ fontSize: "11px", color: "var(--color-text-tertiary)", marginLeft: "auto" }}>
          Active Session
        </span>
      </div>

      <div className="conversation-main" style={{ flex: 1, display: "flex", flexDirection: "column", minHeight: 0 }}>
        <AgriThread />
      </div>
    </section>
  );
}
