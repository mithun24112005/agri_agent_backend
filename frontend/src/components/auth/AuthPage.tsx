import { useState, type FormEvent } from "react";
import { ArrowRight, Check, LoaderCircle, LockKeyhole, Mail, Eye, EyeOff } from "lucide-react";
import { authApi } from "@/lib/api/auth";
import { useAuth } from "@/lib/auth/AuthContext";

export function AuthPage() {
  const { signIn } = useAuth();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const switchMode = (next: "login" | "register") => {
    setMode(next);
    setError("");
    setNotice("");
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");
    setNotice("");
    if (!email.trim()) return setError("Please enter your email address.");
    if (!email.includes("@")) return setError("Please enter a valid email address.");
    if (password.length < 8) return setError("Password must be at least 8 characters.");
    if (mode === "register" && password !== confirmPassword) return setError("Passwords do not match.");

    setIsSubmitting(true);
    try {
      if (mode === "register") {
        await authApi.register(email.trim(), password);
        switchMode("login");
        setNotice("Account created successfully. Please sign in with your credentials.");
      } else {
        await signIn(email.trim(), password);
      }
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Authentication request failed.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="auth-page">
      <div className="auth-atmosphere" aria-hidden="true" />
      <section className="auth-panel">
        <div className="auth-brand" style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <span
            style={{
              width: "10px",
              height: "10px",
              borderRadius: "50%",
              backgroundColor: "var(--color-accent)",
              display: "inline-block",
            }}
          />
          <span style={{ fontSize: "18px", fontWeight: 700, letterSpacing: "-0.02em" }}>CropSage</span>
        </div>
        <div className="auth-copy">
          <p className="eyebrow">Agricultural Decision Support</p>
          <h1>
            Grounded intelligence<br />
            <em>for modern agriculture.</em>
          </h1>
          <p className="auth-subtitle">
            A quiet, precision decision support instrument for crop recommendation, leaf pathology diagnosis, and agronomic management.
          </p>
        </div>
        <div className="auth-note">
          <Check size={15} />
          <span>PostgreSQL-backed session memory and multi-agent traceability.</span>
        </div>
      </section>

      <section className="auth-form-wrap">
        <div className="auth-form-card">
          <div className="auth-tabs" role="tablist" aria-label="Authentication">
            <button
              className={mode === "login" ? "active" : ""}
              onClick={() => switchMode("login")}
              role="tab"
              aria-selected={mode === "login"}
            >
              Sign in
            </button>
            <button
              className={mode === "register" ? "active" : ""}
              onClick={() => switchMode("register")}
              role="tab"
              aria-selected={mode === "register"}
            >
              Create account
            </button>
          </div>

          <div className="form-heading">
            <h2>{mode === "login" ? "Welcome back" : "Create your account"}</h2>
            <p>
              {mode === "login"
                ? "Enter your credentials to access your field consultations."
                : "Sign up to track crop recommendations and diagnosis history."}
            </p>
          </div>

          <form onSubmit={handleSubmit} noValidate>
            <label className="field-label" htmlFor="email">
              Email address
            </label>
            <div className="field-control">
              <Mail size={17} />
              <input
                id="email"
                type="email"
                autoComplete="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="you@domain.com"
              />
            </div>

            <label className="field-label" htmlFor="password">
              Password
            </label>
            <div className="field-control" style={{ position: "relative" }}>
              <LockKeyhole size={17} />
              <input
                id="password"
                type={showPassword ? "text" : "password"}
                autoComplete={mode === "login" ? "current-password" : "new-password"}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="At least 8 characters"
                style={{ paddingRight: "36px" }}
              />
              <button
                type="button"
                onClick={() => setShowPassword((prev) => !prev)}
                aria-label={showPassword ? "Hide password" : "Show password"}
                style={{
                  position: "absolute",
                  right: "10px",
                  top: "50%",
                  transform: "translateY(-50%)",
                  background: "transparent",
                  border: "none",
                  color: "var(--color-text-tertiary)",
                  cursor: "pointer",
                  padding: "4px",
                  display: "grid",
                  placeItems: "center",
                }}
              >
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>

            {mode === "register" && (
              <>
                <label className="field-label" htmlFor="confirm-password">
                  Confirm password
                </label>
                <div className="field-control">
                  <LockKeyhole size={17} />
                  <input
                    id="confirm-password"
                    type={showPassword ? "text" : "password"}
                    autoComplete="new-password"
                    value={confirmPassword}
                    onChange={(event) => setConfirmPassword(event.target.value)}
                    placeholder="Repeat your password"
                  />
                </div>
              </>
            )}

            {error && (
              <div className="form-alert error" role="alert">
                {error}
              </div>
            )}
            {notice && (
              <div className="form-alert success" role="status">
                {notice}
              </div>
            )}

            <button className="primary-button auth-submit" type="submit" disabled={isSubmitting}>
              {isSubmitting ? <LoaderCircle className="spin" size={17} /> : <ArrowRight size={17} />}
              {isSubmitting ? "Verifying…" : mode === "login" ? "Sign in" : "Create account"}
            </button>
          </form>

          <p className="auth-footnote">
            By signing in, you access the ICAR-grounded agricultural decision support system.
          </p>
        </div>
      </section>
    </main>
  );
}
