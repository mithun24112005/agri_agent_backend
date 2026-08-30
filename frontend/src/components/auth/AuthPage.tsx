import { useState, type FormEvent } from "react";
import { ArrowRight, Check, Leaf, LoaderCircle, LockKeyhole, Mail } from "lucide-react";
import { authApi } from "@/lib/api/auth";
import { useAuth } from "@/lib/auth/AuthContext";

export function AuthPage() {
  const { signIn } = useAuth();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
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
    if (!email.trim()) return setError("Enter your email address.");
    if (password.length < 8) return setError("Your password must be at least 8 characters.");
    if (mode === "register" && password !== confirmPassword) return setError("Your passwords don’t match.");
    setIsSubmitting(true);
    try {
      if (mode === "register") {
        await authApi.register(email.trim(), password);
        setNotice("Account created. Sign in to start a new field note.");
        switchMode("login");
      } else {
        await signIn(email.trim(), password);
      }
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "We couldn’t complete that request.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="auth-page">
      <div className="auth-atmosphere" aria-hidden="true" />
      <section className="auth-panel">
        <div className="auth-brand"><span className="brand-mark"><Leaf size={18} strokeWidth={2.3} /></span><span>AgriMind</span></div>
        <div className="auth-copy">
          <p className="eyebrow">Field intelligence, clarified</p>
          <h1>Good decisions<br /><em>start with context.</em></h1>
          <p className="auth-subtitle">A calm, grounded agriculture assistant for crop planning, plant health, and the questions between.</p>
        </div>
        <div className="auth-note"><Check size={15} /><span>Private by design. Your conversations stay tied to your account.</span></div>
      </section>

      <section className="auth-form-wrap">
        <div className="auth-form-card">
          <div className="auth-tabs" role="tablist" aria-label="Authentication">
            <button className={mode === "login" ? "active" : ""} onClick={() => switchMode("login")} role="tab" aria-selected={mode === "login"}>Sign in</button>
            <button className={mode === "register" ? "active" : ""} onClick={() => switchMode("register")} role="tab" aria-selected={mode === "register"}>Create account</button>
          </div>
          <div className="form-heading"><h2>{mode === "login" ? "Welcome back" : "Start your field notebook"}</h2><p>{mode === "login" ? "Continue where your last conversation left off." : "One account for every crop question."}</p></div>
          <form onSubmit={handleSubmit} noValidate>
            <label className="field-label" htmlFor="email">Email address</label>
            <div className="field-control"><Mail size={17} /><input id="email" type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@example.com" /></div>
            <label className="field-label" htmlFor="password">Password</label>
            <div className="field-control"><LockKeyhole size={17} /><input id="password" type="password" autoComplete={mode === "login" ? "current-password" : "new-password"} value={password} onChange={(event) => setPassword(event.target.value)} placeholder="At least 8 characters" /></div>
            {mode === "register" && <><label className="field-label" htmlFor="confirm-password">Confirm password</label><div className="field-control"><LockKeyhole size={17} /><input id="confirm-password" type="password" autoComplete="new-password" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} placeholder="Repeat your password" /></div></>}
            {error && <div className="form-alert error" role="alert">{error}</div>}
            {notice && <div className="form-alert success" role="status">{notice}</div>}
            <button className="primary-button auth-submit" type="submit" disabled={isSubmitting}>{isSubmitting ? <LoaderCircle className="spin" size={17} /> : <ArrowRight size={17} />}{isSubmitting ? "Working…" : mode === "login" ? "Enter AgriMind" : "Create account"}</button>
          </form>
          <p className="auth-footnote">By continuing, you agree to use AgriMind for responsible agricultural decisions.</p>
        </div>
      </section>
    </main>
  );
}
