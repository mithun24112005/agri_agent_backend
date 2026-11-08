import { useState, useRef } from "react";
import { Microscope, UploadCloud, X, AlertCircle, ArrowRight, CheckCircle2, RotateCcw, LoaderCircle } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { sessionsApi } from "@/lib/api/sessions";
import { tokenStorage } from "@/lib/api/client";

interface DiseaseDetectionViewProps {
  onNavigate: (path: string) => void;
}

const MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024; // 5 MB
const ALLOWED_TYPES = ["image/jpeg", "image/png", "image/webp", "image/jpg"];

export function DiseaseDetectionView({ onNavigate }: DiseaseDetectionViewProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [notes, setNotes] = useState("");
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<{
    response: string;
    sessionId: string;
    imagePreview: string;
  } | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = (file: File) => {
    setError(null);
    if (!ALLOWED_TYPES.includes(file.type) && !/\.(jpe?g|png|webp)$/i.test(file.name)) {
      setError("Unsupported file format. Please upload a JPG, PNG, or WEBP image.");
      return;
    }
    if (file.size > MAX_FILE_SIZE_BYTES) {
      setError("File exceeds the 5 MB maximum limit. Please choose a smaller photograph.");
      return;
    }

    setSelectedFile(file);
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelect(e.dataTransfer.files[0]);
    }
  };

  const handleClearFile = () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setSelectedFile(null);
    setPreviewUrl(null);
    setUploadProgress(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile || isProcessing) return;

    setError(null);
    setIsProcessing(true);
    setUploadProgress(0);

    const query = notes.trim() || "Please analyze this plant leaf photo for any signs of disease and provide diagnosis and treatment recommendations.";

    try {
      // 1. Create session
      const session = await sessionsApi.create(`Disease Diagnosis (${selectedFile.name.slice(0, 24)})`);

      // 2. Perform real XMLHttpRequest to track genuine upload byte progress
      const formData = new FormData();
      formData.append("query", query);
      formData.append("session_id", session.id);
      formData.append("file", selectedFile);

      const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "http://localhost:3001").replace(/\/$/, "");

      const response = await new Promise<{ response?: string }>((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open("POST", `${API_BASE_URL}/api/chat`, true);

        const accessToken = tokenStorage.accessToken;
        if (accessToken) {
          xhr.setRequestHeader("Authorization", `Bearer ${accessToken}`);
        }

        xhr.upload.onprogress = (evt) => {
          if (evt.lengthComputable) {
            const percentComplete = Math.round((evt.loaded / evt.total) * 100);
            setUploadProgress(percentComplete);
          }
        };

        xhr.onload = () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            try {
              const data = JSON.parse(xhr.responseText);
              resolve(data);
            } catch {
              reject(new Error("Invalid response format from gateway."));
            }
          } else {
            try {
              const errData = JSON.parse(xhr.responseText);
              reject(new Error(errData?.error?.message ?? errData?.message ?? `Server responded with status ${xhr.status}`));
            } catch {
              reject(new Error(`Upload failed with status ${xhr.status}`));
            }
          }
        };

        xhr.onerror = () => reject(new Error("Network connection error. Check backend status."));
        xhr.send(formData);
      });

      setResult({
        response: response.response || "Analysis completed.",
        sessionId: session.id,
        imagePreview: previewUrl ?? "",
      });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Plant disease diagnosis failed.";
      setError(msg);
    } finally {
      setIsProcessing(false);
      setUploadProgress(null);
    }
  };

  const handleReset = () => {
    handleClearFile();
    setNotes("");
    setResult(null);
    setError(null);
  };

  return (
    <div
      className="feature-page disease-page"
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
              backgroundColor: "var(--color-agent-disease-bg)",
              color: "var(--color-agent-disease)",
            }}
          >
            <Microscope size={16} />
          </span>
          <h1 style={{ margin: 0, fontSize: "20px", fontWeight: 700, color: "var(--color-text-primary)" }}>
            Plant Disease Diagnosis Workstation
          </h1>
        </div>
        <p style={{ margin: 0, fontSize: "14px", color: "var(--color-text-secondary)", lineHeight: 1.5 }}>
          Upload high-resolution photographs of diseased foliage or plant parts. The integrated vision model
          identifies the crop species, verifies leaf health, and provides grounded disease management recommendations.
        </p>
      </div>

      {result ? (
        /* Result view */
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
                Diagnosis & Agronomic Advisory
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
              <span>Diagnose Another Photo</span>
            </button>
          </div>

          {/* Photo Preview thumbnail */}
          {result.imagePreview && (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "14px",
                padding: "12px",
                borderRadius: "var(--radius-sm)",
                backgroundColor: "var(--color-sunken)",
              }}
            >
              <img
                src={result.imagePreview}
                alt="Analyzed leaf"
                style={{
                  width: "72px",
                  height: "72px",
                  objectFit: "cover",
                  borderRadius: "var(--radius-sm)",
                  border: "1px solid var(--color-border-strong)",
                }}
              />
              <div style={{ display: "flex", flexDirection: "column", gap: "2px", fontSize: "12px" }}>
                <strong style={{ color: "var(--color-text-primary)" }}>Leaf Image Processed</strong>
                <span style={{ color: "var(--color-text-secondary)" }}>
                  Visual features evaluated against plant pathology dataset.
                </span>
              </div>
            </div>
          )}

          {/* Markdown Content */}
          <div className="markdown" style={{ fontSize: "14px", lineHeight: 1.6 }}>
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{result.response}</ReactMarkdown>
          </div>

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
                backgroundColor: "var(--color-agent-disease)",
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
        /* Upload Form */
        <form
          className="surface-form"
          onSubmit={handleSubmit}
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
          {/* Dropzone */}
          <div
            onDragOver={(e) => e.preventDefault()}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              padding: "36px 20px",
              borderRadius: "var(--radius-md)",
              border: "2px dashed var(--color-border-strong)",
              backgroundColor: "var(--color-canvas)",
              cursor: "pointer",
              textAlign: "center",
              transition: "border-color 0.15s ease",
            }}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".jpg,.jpeg,.png,.webp"
              style={{ display: "none" }}
              onChange={(e) => {
                if (e.target.files && e.target.files[0]) {
                  handleFileSelect(e.target.files[0]);
                }
              }}
            />

            {previewUrl ? (
              <div
                style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "12px" }}
                onClick={(e) => e.stopPropagation()}
              >
                <div style={{ position: "relative" }}>
                  <img
                    src={previewUrl}
                    alt="Selected plant leaf"
                    style={{
                      maxHeight: "220px",
                      maxWidth: "100%",
                      borderRadius: "var(--radius-sm)",
                      border: "1px solid var(--color-border-strong)",
                      objectFit: "contain",
                    }}
                  />
                  <button
                    type="button"
                    onClick={handleClearFile}
                    aria-label="Remove photograph"
                    style={{
                      position: "absolute",
                      top: "-8px",
                      right: "-8px",
                      width: "24px",
                      height: "24px",
                      borderRadius: "50%",
                      backgroundColor: "var(--color-text-primary)",
                      color: "var(--color-surface)",
                      border: "none",
                      display: "grid",
                      placeItems: "center",
                      cursor: "pointer",
                    }}
                  >
                    <X size={14} />
                  </button>
                </div>
                <span style={{ fontSize: "12px", color: "var(--color-text-secondary)" }}>
                  {selectedFile?.name} ({(selectedFile ? selectedFile.size / 1024 : 0).toFixed(0)} KB)
                </span>
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "10px" }}>
                <span
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    justifyContent: "center",
                    width: "44px",
                    height: "44px",
                    borderRadius: "50%",
                    backgroundColor: "var(--color-sunken)",
                    color: "var(--color-accent)",
                  }}
                >
                  <UploadCloud size={24} />
                </span>
                <div>
                  <strong style={{ fontSize: "14px", color: "var(--color-text-primary)", display: "block" }}>
                    Click or drag leaf photograph here
                  </strong>
                  <span style={{ fontSize: "12px", color: "var(--color-text-tertiary)" }}>
                    Supported formats: JPG, PNG, WEBP (Max: 5 MB)
                  </span>
                </div>
              </div>
            )}
          </div>

          {/* Notes Input */}
          <div>
            <label
              htmlFor="symptom-notes"
              style={{
                display: "block",
                fontSize: "12px",
                fontWeight: 500,
                color: "var(--color-text-secondary)",
                marginBottom: "6px",
              }}
            >
              Additional Observations or Symptoms (Optional)
            </label>
            <textarea
              id="symptom-notes"
              rows={3}
              placeholder="e.g. Yellowing observed on lower foliage since 3 days ago, accompanied by brown spots."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              style={{
                width: "100%",
                padding: "10px 12px",
                borderRadius: "var(--radius-sm)",
                border: "1px solid var(--color-border-strong)",
                backgroundColor: "var(--color-canvas)",
                color: "var(--color-text-primary)",
                fontSize: "13px",
                outline: "none",
                resize: "vertical",
              }}
            />
          </div>

          {/* Upload Progress Bar if active */}
          {uploadProgress !== null && (
            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px", color: "var(--color-text-secondary)" }}>
                <span>Uploading photograph to inference server…</span>
                <strong>{uploadProgress}%</strong>
              </div>
              <div
                style={{
                  width: "100%",
                  height: "6px",
                  borderRadius: "999px",
                  backgroundColor: "var(--color-sunken)",
                  overflow: "hidden",
                }}
              >
                <div
                  style={{
                    width: `${uploadProgress}%`,
                    height: "100%",
                    backgroundColor: "var(--color-accent)",
                    transition: "width 0.15s ease",
                  }}
                />
              </div>
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

          {/* Submit Action */}
          <div style={{ display: "flex", justifyContent: "flex-end", paddingTop: "8px" }}>
            <button
              type="submit"
              disabled={!selectedFile || isProcessing}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "8px",
                padding: "9px 20px",
                borderRadius: "var(--radius-sm)",
                backgroundColor: selectedFile ? "var(--color-agent-disease)" : "var(--color-sunken)",
                color: selectedFile ? "#FFFFFF" : "var(--color-text-tertiary)",
                border: "none",
                fontSize: "13px",
                fontWeight: 600,
                cursor: selectedFile && !isProcessing ? "pointer" : "not-allowed",
              }}
            >
              {isProcessing ? (
                <>
                  <LoaderCircle size={15} className="spin animate-spin" />
                  <span>Analyzing foliage…</span>
                </>
              ) : (
                <>
                  <span>Diagnose Photograph</span>
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
