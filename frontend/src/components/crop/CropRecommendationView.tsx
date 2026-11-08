import { useState, useId } from "react";
import { Wheat, CheckCircle2, AlertCircle, ArrowRight, LoaderCircle, RotateCcw } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { chatApi } from "@/lib/api/chat";
import { sessionsApi } from "@/lib/api/sessions";

interface CropRecommendationViewProps {
  onNavigate: (path: string) => void;
}

interface CropFormValues {
  N: string;
  P: string;
  K: string;
  ph: string;
  temperature: string;
  humidity: string;
  rainfall: string;
}

const initialValues: CropFormValues = {
  N: "",
  P: "",
  K: "",
  ph: "",
  temperature: "",
  humidity: "",
  rainfall: "",
};

export function CropRecommendationView({ onNavigate }: CropRecommendationViewProps) {
  const [values, setValues] = useState<CropFormValues>(initialValues);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<{
    response: string;
    submittedValues: CropFormValues;
    sessionId: string;
  } | null>(null);

  const nId = useId();
  const pId = useId();
  const kId = useId();
  const phId = useId();
  const tempId = useId();
  const humId = useId();
  const rainId = useId();

  const handleChange = (field: keyof CropFormValues, val: string) => {
    setValues((prev) => ({ ...prev, [field]: val }));
    setError(null);
  };

  // Validate all 7 fields against physical boundaries
  const getValidationErrors = (): { missing: string[]; invalid: string[] } => {
    const missing: string[] = [];
    const invalid: string[] = [];

    const checkField = (field: keyof CropFormValues, label: string, min: number, max: number) => {
      const raw = values[field].trim();
      if (!raw) {
        missing.push(label);
        return;
      }
      const num = parseFloat(raw);
      if (isNaN(num) || num < min || num > max) {
        invalid.push(`${label} (${min} to ${max})`);
      }
    };

    checkField("N", "Nitrogen (N)", 0, 300);
    checkField("P", "Phosphorus (P)", 0, 200);
    checkField("K", "Potassium (K)", 0, 300);
    checkField("ph", "Soil pH", 0.0, 14.0);
    checkField("temperature", "Temperature", -50, 70);
    checkField("humidity", "Humidity", 0, 100);
    checkField("rainfall", "Rainfall", 0, 2000);

    return { missing, invalid };
  };

  const { missing, invalid } = getValidationErrors();
  const isFormComplete = missing.length === 0 && invalid.length === 0;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isFormComplete || isSubmitting) return;

    setIsSubmitting(true);
    setError(null);

    try {
      // 1. Create a dedicated session for this recommendation
      const session = await sessionsApi.create(
        `Crop Advice (N:${values.N} P:${values.P} K:${values.K})`
      );

      // 2. Format query using the exact 7 parameters recognized by the Supervisor gate
      const query = `My soil has N=${values.N}, P=${values.P}, K=${values.K}, pH=${values.ph}, temperature=${values.temperature}°C, humidity=${values.humidity}%, rainfall=${values.rainfall}mm. Which crop is suitable?`;

      // 3. Send query to Gateway
      const res = await chatApi.send(query, session.id);

      setResult({
        response: res.response || "Recommendation completed.",
        submittedValues: { ...values },
        sessionId: session.id,
      });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to calculate crop recommendation.";
      setError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReset = () => {
    setValues(initialValues);
    setResult(null);
    setError(null);
  };

  return (
    <div
      className="feature-page crop-page"
      style={{
        maxWidth: "860px",
        width: "100%",
        margin: "0 auto",
        padding: "32px 20px 48px",
        display: "flex",
        flexDirection: "column",
        gap: "24px",
      }}
    >
      {/* Title & Introduction */}
      <div>
        <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "6px" }}>
          <span
            style={{
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              width: "28px",
              height: "28px",
              borderRadius: "var(--radius-sm)",
              backgroundColor: "var(--color-agent-crop-bg)",
              color: "var(--color-agent-crop)",
            }}
          >
            <Wheat size={16} />
          </span>
          <h1 style={{ margin: 0, fontSize: "20px", fontWeight: 700, color: "var(--color-text-primary)" }}>
            Crop Recommendation Workstation
          </h1>
        </div>
        <p style={{ margin: 0, fontSize: "14px", color: "var(--color-text-secondary)", lineHeight: 1.5 }}>
          The Crop Recommendation Agent requires all seven parameters to evaluate soil fertility, climate suitability,
          and harvest viability. Incomplete queries are blocked by the Supervisor gate to avoid misleading guidance.
        </p>
      </div>

      {/* Result Card if available */}
      {result ? (
        <div className="result-panel"
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "20px",
            backgroundColor: "var(--color-surface)",
            border: "1px solid var(--color-border-subtle)",
            borderRadius: "var(--radius-md)",
            padding: "24px",
            boxShadow: "var(--shadow-sm)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <CheckCircle2 size={18} style={{ color: "var(--color-status-success)" }} />
              <h2 style={{ margin: 0, fontSize: "16px", fontWeight: 600, color: "var(--color-text-primary)" }}>
                Agronomic Evaluation Result
              </h2>
            </div>
            <button
              type="button"
              onClick={handleReset}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "6px",
                background: "transparent",
                border: "1px solid var(--color-border-subtle)",
                borderRadius: "var(--radius-sm)",
                padding: "6px 12px",
                fontSize: "12px",
                color: "var(--color-text-secondary)",
                cursor: "pointer",
              }}
            >
              <RotateCcw size={13} />
              <span>New Calculation</span>
            </button>
          </div>

          {/* Submitted Values Audit Card */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(100px, 1fr))",
              gap: "8px",
              padding: "12px 14px",
              backgroundColor: "var(--color-sunken)",
              borderRadius: "var(--radius-sm)",
              fontSize: "12px",
            }}
          >
            <div>
              <span style={{ color: "var(--color-text-tertiary)", display: "block" }}>Nitrogen (N)</span>
              <strong style={{ color: "var(--color-text-primary)" }}>{result.submittedValues.N} kg/ha</strong>
            </div>
            <div>
              <span style={{ color: "var(--color-text-tertiary)", display: "block" }}>Phosphorus (P)</span>
              <strong style={{ color: "var(--color-text-primary)" }}>{result.submittedValues.P} kg/ha</strong>
            </div>
            <div>
              <span style={{ color: "var(--color-text-tertiary)", display: "block" }}>Potassium (K)</span>
              <strong style={{ color: "var(--color-text-primary)" }}>{result.submittedValues.K} kg/ha</strong>
            </div>
            <div>
              <span style={{ color: "var(--color-text-tertiary)", display: "block" }}>pH</span>
              <strong style={{ color: "var(--color-text-primary)" }}>{result.submittedValues.ph}</strong>
            </div>
            <div>
              <span style={{ color: "var(--color-text-tertiary)", display: "block" }}>Temperature</span>
              <strong style={{ color: "var(--color-text-primary)" }}>{result.submittedValues.temperature} °C</strong>
            </div>
            <div>
              <span style={{ color: "var(--color-text-tertiary)", display: "block" }}>Humidity</span>
              <strong style={{ color: "var(--color-text-primary)" }}>{result.submittedValues.humidity} %</strong>
            </div>
            <div>
              <span style={{ color: "var(--color-text-tertiary)", display: "block" }}>Rainfall</span>
              <strong style={{ color: "var(--color-text-primary)" }}>{result.submittedValues.rainfall} mm</strong>
            </div>
          </div>

          {/* Markdown Content */}
          <div className="markdown" style={{ fontSize: "14px", lineHeight: 1.6 }}>
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{result.response}</ReactMarkdown>
          </div>

          {/* Follow up link */}
          <div style={{ display: "flex", justifyContent: "flex-end", paddingTop: "12px", borderTop: "1px solid var(--color-border-subtle)" }}>
            <button
              type="button"
              onClick={() => onNavigate(`chat/${result.sessionId}`)}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                padding: "8px 16px",
                borderRadius: "var(--radius-sm)",
                backgroundColor: "var(--color-accent)",
                color: "#FFFFFF",
                border: "none",
                fontSize: "13px",
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              <span>Continue in Chat Consultation</span>
              <ArrowRight size={14} />
            </button>
          </div>
        </div>
      ) : (
        /* Form view */
        <form
          className="surface-form"
          onSubmit={handleSubmit}
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "24px",
            backgroundColor: "var(--color-surface)",
            border: "1px solid var(--color-border-subtle)",
            borderRadius: "var(--radius-md)",
            padding: "24px",
            boxShadow: "var(--shadow-sm)",
          }}
        >
          {/* Section 1: Soil Macro-Nutrients */}
          <fieldset style={{ border: "none", margin: 0, padding: 0, display: "flex", flexDirection: "column", gap: "12px" }}>
            <legend style={{ fontSize: "13px", fontWeight: 600, color: "var(--color-text-primary)", marginBottom: "4px" }}>
              1. Soil Macro-Nutrients (Primary NPK)
            </legend>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "16px" }}>
              <div>
                <label htmlFor={nId} style={{ display: "block", fontSize: "12px", fontWeight: 500, color: "var(--color-text-secondary)", marginBottom: "4px" }}>
                  Nitrogen (N) — kg/ha
                </label>
                <input
                  id={nId}
                  type="number"
                  step="any"
                  placeholder="e.g. 90 (0 - 300)"
                  value={values.N}
                  onChange={(e) => handleChange("N", e.target.value)}
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    borderRadius: "var(--radius-sm)",
                    border: "1px solid var(--color-border-strong)",
                    backgroundColor: "var(--color-canvas)",
                    color: "var(--color-text-primary)",
                    fontSize: "13px",
                    outline: "none",
                  }}
                />
              </div>

              <div>
                <label htmlFor={pId} style={{ display: "block", fontSize: "12px", fontWeight: 500, color: "var(--color-text-secondary)", marginBottom: "4px" }}>
                  Phosphorus (P) — kg/ha
                </label>
                <input
                  id={pId}
                  type="number"
                  step="any"
                  placeholder="e.g. 42 (0 - 200)"
                  value={values.P}
                  onChange={(e) => handleChange("P", e.target.value)}
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    borderRadius: "var(--radius-sm)",
                    border: "1px solid var(--color-border-strong)",
                    backgroundColor: "var(--color-canvas)",
                    color: "var(--color-text-primary)",
                    fontSize: "13px",
                    outline: "none",
                  }}
                />
              </div>

              <div>
                <label htmlFor={kId} style={{ display: "block", fontSize: "12px", fontWeight: 500, color: "var(--color-text-secondary)", marginBottom: "4px" }}>
                  Potassium (K) — kg/ha
                </label>
                <input
                  id={kId}
                  type="number"
                  step="any"
                  placeholder="e.g. 43 (0 - 300)"
                  value={values.K}
                  onChange={(e) => handleChange("K", e.target.value)}
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    borderRadius: "var(--radius-sm)",
                    border: "1px solid var(--color-border-strong)",
                    backgroundColor: "var(--color-canvas)",
                    color: "var(--color-text-primary)",
                    fontSize: "13px",
                    outline: "none",
                  }}
                />
              </div>
            </div>
          </fieldset>

          <div style={{ height: "1px", backgroundColor: "var(--color-border-subtle)" }} />

          {/* Section 2: Soil Chemistry */}
          <fieldset style={{ border: "none", margin: 0, padding: 0, display: "flex", flexDirection: "column", gap: "12px" }}>
            <legend style={{ fontSize: "13px", fontWeight: 600, color: "var(--color-text-primary)", marginBottom: "4px" }}>
              2. Soil Reaction (pH)
            </legend>
            <div style={{ maxWidth: "260px" }}>
              <label htmlFor={phId} style={{ display: "block", fontSize: "12px", fontWeight: 500, color: "var(--color-text-secondary)", marginBottom: "4px" }}>
                Soil pH (0.0 to 14.0)
              </label>
              <input
                id={phId}
                type="number"
                step="0.1"
                placeholder="e.g. 6.5 (Neutral: 6.0-7.5)"
                value={values.ph}
                onChange={(e) => handleChange("ph", e.target.value)}
                style={{
                  width: "100%",
                  padding: "8px 12px",
                  borderRadius: "var(--radius-sm)",
                  border: "1px solid var(--color-border-strong)",
                  backgroundColor: "var(--color-canvas)",
                  color: "var(--color-text-primary)",
                  fontSize: "13px",
                  outline: "none",
                }}
              />
            </div>
          </fieldset>

          <div style={{ height: "1px", backgroundColor: "var(--color-border-subtle)" }} />

          {/* Section 3: Weather & Climate */}
          <fieldset style={{ border: "none", margin: 0, padding: 0, display: "flex", flexDirection: "column", gap: "12px" }}>
            <legend style={{ fontSize: "13px", fontWeight: 600, color: "var(--color-text-primary)", marginBottom: "4px" }}>
              3. Climate & Environmental Conditions
            </legend>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "16px" }}>
              <div>
                <label htmlFor={tempId} style={{ display: "block", fontSize: "12px", fontWeight: 500, color: "var(--color-text-secondary)", marginBottom: "4px" }}>
                  Temperature (°C)
                </label>
                <input
                  id={tempId}
                  type="number"
                  step="0.1"
                  placeholder="e.g. 25.0 (-50 to 70°C)"
                  value={values.temperature}
                  onChange={(e) => handleChange("temperature", e.target.value)}
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    borderRadius: "var(--radius-sm)",
                    border: "1px solid var(--color-border-strong)",
                    backgroundColor: "var(--color-canvas)",
                    color: "var(--color-text-primary)",
                    fontSize: "13px",
                    outline: "none",
                  }}
                />
              </div>

              <div>
                <label htmlFor={humId} style={{ display: "block", fontSize: "12px", fontWeight: 500, color: "var(--color-text-secondary)", marginBottom: "4px" }}>
                  Relative Humidity (%)
                </label>
                <input
                  id={humId}
                  type="number"
                  step="0.1"
                  placeholder="e.g. 80 (0 to 100%)"
                  value={values.humidity}
                  onChange={(e) => handleChange("humidity", e.target.value)}
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    borderRadius: "var(--radius-sm)",
                    border: "1px solid var(--color-border-strong)",
                    backgroundColor: "var(--color-canvas)",
                    color: "var(--color-text-primary)",
                    fontSize: "13px",
                    outline: "none",
                  }}
                />
              </div>

              <div>
                <label htmlFor={rainId} style={{ display: "block", fontSize: "12px", fontWeight: 500, color: "var(--color-text-secondary)", marginBottom: "4px" }}>
                  Seasonal Rainfall (mm)
                </label>
                <input
                  id={rainId}
                  type="number"
                  step="0.1"
                  placeholder="e.g. 200 (0 to 2000mm)"
                  value={values.rainfall}
                  onChange={(e) => handleChange("rainfall", e.target.value)}
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    borderRadius: "var(--radius-sm)",
                    border: "1px solid var(--color-border-strong)",
                    backgroundColor: "var(--color-canvas)",
                    color: "var(--color-text-primary)",
                    fontSize: "13px",
                    outline: "none",
                  }}
                />
              </div>
            </div>
          </fieldset>

          {/* Validation & Incomplete Parameter Feedback */}
          {!isFormComplete && (
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                gap: "6px",
                padding: "12px 14px",
                borderRadius: "var(--radius-sm)",
                backgroundColor: "var(--color-status-warning-bg)",
                border: "1px solid var(--color-status-warning)",
                color: "var(--color-status-warning)",
                fontSize: "13px",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "8px", fontWeight: 600 }}>
                <AlertCircle size={15} />
                <span>Input Completeness Gate:</span>
              </div>
              {missing.length > 0 && (
                <div>
                  Missing parameters: <strong>{missing.join(", ")}</strong>
                </div>
              )}
              {invalid.length > 0 && (
                <div>
                  Out of plausible bounds: <strong>{invalid.join(", ")}</strong>
                </div>
              )}
            </div>
          )}

          {error && (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                padding: "12px 14px",
                borderRadius: "var(--radius-sm)",
                backgroundColor: "var(--color-status-error-bg)",
                border: "1px solid var(--color-status-error)",
                color: "var(--color-status-error)",
                fontSize: "13px",
              }}
            >
              <AlertCircle size={15} />
              <span>{error}</span>
            </div>
          )}

          {/* Action Row */}
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", paddingTop: "8px" }}>
            <span style={{ fontSize: "12px", color: "var(--color-text-tertiary)" }}>
              {isFormComplete ? "All 7 parameters verified." : "Complete all 7 fields to enable calculation."}
            </span>

            <button
              type="submit"
              disabled={!isFormComplete || isSubmitting}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "8px",
                padding: "9px 20px",
                borderRadius: "var(--radius-sm)",
                backgroundColor: isFormComplete ? "var(--color-accent)" : "var(--color-sunken)",
                color: isFormComplete ? "#FFFFFF" : "var(--color-text-tertiary)",
                border: "none",
                fontSize: "13px",
                fontWeight: 600,
                cursor: isFormComplete && !isSubmitting ? "pointer" : "not-allowed",
                transition: "background-color 0.15s ease",
              }}
            >
              {isSubmitting ? (
                <>
                  <LoaderCircle size={15} className="spin animate-spin" />
                  <span>Evaluating suitability…</span>
                </>
              ) : (
                <>
                  <span>Calculate Recommendation</span>
                  <ArrowRight size={14} />
                </>
              )}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}

