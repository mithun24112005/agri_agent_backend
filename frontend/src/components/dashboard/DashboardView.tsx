import { useEffect, useState } from "react";
import { Wheat, Microscope, MessageSquare, ArrowRight, Clock, ShieldCheck, Cpu } from "lucide-react";
import { useAuth } from "@/lib/auth/AuthContext";
import { sessionsApi } from "@/lib/api/sessions";
import type { Session } from "@/types/api";

interface DashboardViewProps {
  onNavigate: (path: string) => void;
}

export function DashboardView({ onNavigate }: DashboardViewProps) {
  const { user } = useAuth();
  const [sessions, setSessions] = useState<Session[]>([]);
  const [isLoadingSessions, setIsLoadingSessions] = useState(true);

  useEffect(() => {
    let isMounted = true;
    sessionsApi
      .list()
      .then((data) => {
        if (isMounted) setSessions(data.slice(0, 5));
      })
      .catch(() => {
        // Non-blocking: fail quietly if sessions cannot be listed
      })
      .finally(() => {
        if (isMounted) setIsLoadingSessions(false);
      });
    return () => {
      isMounted = false;
    };
  }, []);

  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return "Good morning";
    if (hour < 17) return "Good afternoon";
    return "Good evening";
  };

  const formatRelativeTime = (dateString: string) => {
    try {
      const date = new Date(dateString);
      const now = new Date();
      const diffMs = now.getTime() - date.getTime();
      const diffMins = Math.floor(diffMs / (1000 * 60));
      const diffHours = Math.floor(diffMins / 60);
      const diffDays = Math.floor(diffHours / 24);

      if (diffMins < 2) return "just now";
      if (diffMins < 60) return `${diffMins}m ago`;
      if (diffHours < 24) return `${diffHours}h ago`;
      if (diffDays === 1) return "yesterday";
      return `${diffDays}d ago`;
    } catch {
      return "";
    }
  };

  const displayName = user?.email ? user.email.split("@")[0] : "Farmer";

  return (
    <div
      className="feature-page dashboard-page"
      style={{
        maxWidth: "960px",
        width: "100%",
        margin: "0 auto",
        padding: "32px 24px 48px",
        display: "flex",
        flexDirection: "column",
        gap: "32px",
      }}
    >
      {/* Header Banner */}
      <section style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span
            style={{
              fontSize: "11px",
              fontWeight: 600,
              letterSpacing: "0.08em",
              textTransform: "uppercase",
              color: "var(--color-accent)",
              backgroundColor: "var(--color-accent-subtle)",
              padding: "3px 8px",
              borderRadius: "4px",
            }}
          >
            Decision Support System
          </span>
          <span style={{ fontSize: "12px", color: "var(--color-text-tertiary)" }}>
            {new Date().toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" })}
          </span>
        </div>
        <h1
          style={{
            margin: "4px 0 0",
            fontSize: "26px",
            fontWeight: 700,
            letterSpacing: "-0.02em",
            color: "var(--color-text-primary)",
          }}
        >
          {getGreeting()}, {displayName}
        </h1>
        <p
          style={{
            margin: 0,
            fontSize: "14px",
            color: "var(--color-text-secondary)",
            maxWidth: "600px",
            lineHeight: 1.5,
          }}
        >
          Welcome to your agricultural command desk. Access specialized AI agents for crop recommendations,
          plant pathology diagnosis, and agronomic management.
        </p>
      </section>

      {/* Quick Start Action Cards */}
      <section style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
        <h2
          style={{
            margin: 0,
            fontSize: "13px",
            fontWeight: 600,
            textTransform: "uppercase",
            letterSpacing: "0.06em",
            color: "var(--color-text-tertiary)",
          }}
        >
          Workstations & Workflows
        </h2>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
            gap: "16px",
          }}
        >
          {/* Card 1: Crop Recommendation */}
          <div
            className="feature-card"
            onClick={() => onNavigate("crop")}
            style={{
              display: "flex",
              flexDirection: "column",
              justifyContent: "space-between",
              padding: "20px",
              borderRadius: "var(--radius-md)",
              backgroundColor: "var(--color-surface)",
              border: "1px solid var(--color-border-subtle)",
              boxShadow: "var(--shadow-sm)",
              cursor: "pointer",
              transition: "transform 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = "var(--color-agent-crop)";
              e.currentTarget.style.transform = "translateY(-1px)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = "var(--color-border-subtle)";
              e.currentTarget.style.transform = "none";
            }}
          >
            <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
              <div
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                  width: "36px",
                  height: "36px",
                  borderRadius: "var(--radius-sm)",
                  backgroundColor: "var(--color-agent-crop-bg)",
                  color: "var(--color-agent-crop)",
                }}
              >
                <Wheat size={20} />
              </div>
              <h3 style={{ margin: 0, fontSize: "16px", fontWeight: 600, color: "var(--color-text-primary)" }}>
                Crop Recommendation
              </h3>
              <p style={{ margin: 0, fontSize: "13px", color: "var(--color-text-secondary)", lineHeight: 1.5 }}>
                Submit all 7 soil nutrients (N, P, K), pH, and climate measurements to identify optimal crops.
              </p>
            </div>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "6px",
                marginTop: "16px",
                fontSize: "13px",
                fontWeight: 600,
                color: "var(--color-agent-crop)",
              }}
            >
              <span>Open Guided Form</span>
              <ArrowRight size={14} />
            </div>
          </div>

          {/* Card 2: Plant Disease Diagnosis */}
          <div
            className="feature-card"
            onClick={() => onNavigate("disease")}
            style={{
              display: "flex",
              flexDirection: "column",
              justifyContent: "space-between",
              padding: "20px",
              borderRadius: "var(--radius-md)",
              backgroundColor: "var(--color-surface)",
              border: "1px solid var(--color-border-subtle)",
              boxShadow: "var(--shadow-sm)",
              cursor: "pointer",
              transition: "transform 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = "var(--color-agent-disease)";
              e.currentTarget.style.transform = "translateY(-1px)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = "var(--color-border-subtle)";
              e.currentTarget.style.transform = "none";
            }}
          >
            <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
              <div
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                  width: "36px",
                  height: "36px",
                  borderRadius: "var(--radius-sm)",
                  backgroundColor: "var(--color-agent-disease-bg)",
                  color: "var(--color-agent-disease)",
                }}
              >
                <Microscope size={20} />
              </div>
              <h3 style={{ margin: 0, fontSize: "16px", fontWeight: 600, color: "var(--color-text-primary)" }}>
                Disease Diagnosis
              </h3>
              <p style={{ margin: 0, fontSize: "13px", color: "var(--color-text-secondary)", lineHeight: 1.5 }}>
                Upload plant leaf photographs (up to 5 MB) for automated vision diagnosis and treatment guidelines.
              </p>
            </div>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "6px",
                marginTop: "16px",
                fontSize: "13px",
                fontWeight: 600,
                color: "var(--color-agent-disease)",
              }}
            >
              <span>Upload Photograph</span>
              <ArrowRight size={14} />
            </div>
          </div>

          {/* Card 3: General Agronomic Inquiry */}
          <div
            className="feature-card"
            onClick={() => onNavigate("chat")}
            style={{
              display: "flex",
              flexDirection: "column",
              justifyContent: "space-between",
              padding: "20px",
              borderRadius: "var(--radius-md)",
              backgroundColor: "var(--color-surface)",
              border: "1px solid var(--color-border-subtle)",
              boxShadow: "var(--shadow-sm)",
              cursor: "pointer",
              transition: "transform 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = "var(--color-agent-general)";
              e.currentTarget.style.transform = "translateY(-1px)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = "var(--color-border-subtle)";
              e.currentTarget.style.transform = "none";
            }}
          >
            <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
              <div
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                  width: "36px",
                  height: "36px",
                  borderRadius: "var(--radius-sm)",
                  backgroundColor: "var(--color-agent-general-bg)",
                  color: "var(--color-agent-general)",
                }}
              >
                <MessageSquare size={20} />
              </div>
              <h3 style={{ margin: 0, fontSize: "16px", fontWeight: 600, color: "var(--color-text-primary)" }}>
                Chat Consultation
              </h3>
              <p style={{ margin: 0, fontSize: "13px", color: "var(--color-text-secondary)", lineHeight: 1.5 }}>
                Ask questions regarding fertilizer schedules, soil amendments, ICAR guidelines, and farming practices.
              </p>
            </div>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "6px",
                marginTop: "16px",
                fontSize: "13px",
                fontWeight: 600,
                color: "var(--color-agent-general)",
              }}
            >
              <span>Start Consultation</span>
              <ArrowRight size={14} />
            </div>
          </div>
        </div>
      </section>

      {/* Grid: Recent Sessions & System Architecture */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
          gap: "24px",
        }}
      >
        {/* Recent Consultations */}
        <section className="data-panel"
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "12px",
            backgroundColor: "var(--color-surface)",
            padding: "20px",
            borderRadius: "var(--radius-md)",
            border: "1px solid var(--color-border-subtle)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <h2
              style={{
                margin: 0,
                fontSize: "14px",
                fontWeight: 600,
                color: "var(--color-text-primary)",
              }}
            >
              Recent Consultations
            </h2>
            <button
              type="button"
              onClick={() => onNavigate("chat")}
              style={{
                background: "transparent",
                border: "none",
                fontSize: "12px",
                fontWeight: 500,
                color: "var(--color-accent)",
                cursor: "pointer",
              }}
            >
              View all
            </button>
          </div>

          {isLoadingSessions ? (
            <div style={{ padding: "20px 0", textAlign: "center", color: "var(--color-text-tertiary)", fontSize: "13px" }}>
              Loading sessions…
            </div>
          ) : sessions.length === 0 ? (
            <div
              style={{
                padding: "24px 16px",
                textAlign: "center",
                backgroundColor: "var(--color-sunken)",
                borderRadius: "var(--radius-sm)",
                color: "var(--color-text-secondary)",
                fontSize: "13px",
              }}
            >
              No past consultations found. Start your first session above.
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              {sessions.map((s) => (
                <div
                  key={s.id}
                  onClick={() => onNavigate(`chat/${s.id}`)}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "10px 12px",
                    borderRadius: "var(--radius-sm)",
                    backgroundColor: "var(--color-canvas)",
                    border: "1px solid var(--color-border-subtle)",
                    cursor: "pointer",
                    transition: "border-color 0.15s ease",
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.borderColor = "var(--color-accent)";
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.borderColor = "var(--color-border-subtle)";
                  }}
                >
                  <span
                    style={{
                      fontSize: "13px",
                      fontWeight: 500,
                      color: "var(--color-text-primary)",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                      maxWidth: "230px",
                    }}
                  >
                    {s.title}
                  </span>
                  <span
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "4px",
                      fontSize: "11px",
                      color: "var(--color-text-tertiary)",
                      flexShrink: 0,
                    }}
                  >
                    <Clock size={12} />
                    {formatRelativeTime(s.updatedAt)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* System Capabilities & Grounding Notice */}
        <section className="data-panel"
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "12px",
            backgroundColor: "var(--color-surface)",
            padding: "20px",
            borderRadius: "var(--radius-md)",
            border: "1px solid var(--color-border-subtle)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <Cpu size={16} style={{ color: "var(--color-accent)" }} />
            <h2
              style={{
                margin: 0,
                fontSize: "14px",
                fontWeight: 600,
                color: "var(--color-text-primary)",
              }}
            >
              Engine Architecture & Verification
            </h2>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "10px", fontSize: "12px", lineHeight: 1.5 }}>
            <div
              style={{
                display: "flex",
                gap: "8px",
                padding: "8px 10px",
                borderRadius: "var(--radius-sm)",
                backgroundColor: "var(--color-sunken)",
              }}
            >
              <ShieldCheck size={16} style={{ color: "var(--color-status-success)", flexShrink: 0, marginTop: "2px" }} />
              <div>
                <strong style={{ color: "var(--color-text-primary)", display: "block" }}>Supervisor Gate</strong>
                <span style={{ color: "var(--color-text-secondary)" }}>
                  Strict 7-parameter completeness verification for crop recommendations; standalone fertilizer inquiries route exclusively to the General Agent.
                </span>
              </div>
            </div>

            <div
              style={{
                display: "flex",
                gap: "8px",
                padding: "8px 10px",
                borderRadius: "var(--radius-sm)",
                backgroundColor: "var(--color-sunken)",
              }}
            >
              <ShieldCheck size={16} style={{ color: "var(--color-status-success)", flexShrink: 0, marginTop: "2px" }} />
              <div>
                <strong style={{ color: "var(--color-text-primary)", display: "block" }}>ML Models</strong>
                <span style={{ color: "var(--color-text-secondary)" }}>
                  Random Forest multi-class crop classifier & MobileNet-V2 PlantVillage 38-class plant pathology vision detector.
                </span>
              </div>
            </div>

            <div
              style={{
                display: "flex",
                gap: "8px",
                padding: "8px 10px",
                borderRadius: "var(--radius-sm)",
                backgroundColor: "var(--color-sunken)",
              }}
            >
              <ShieldCheck size={16} style={{ color: "var(--color-status-success)", flexShrink: 0, marginTop: "2px" }} />
              <div>
                <strong style={{ color: "var(--color-text-primary)", display: "block" }}>Grounded Agronomy</strong>
                <span style={{ color: "var(--color-text-secondary)" }}>
                  RAG pipelines backed by ICAR soil testing benchmarks, crop calendars, and official government advisory guidelines.
                </span>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
