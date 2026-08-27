"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { signIn } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (loading) return;

    setLoading(true);
    setError(null);
    try {
      await signIn(identifier, password, remember);
      router.replace("/app/overview");
      router.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to sign in.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-brand-panel" aria-label="DomainTwin AI product context">
        <Link className="brand brand--dark" href="/">
          <span className="brand-mark">D</span>
          <span>DomainTwin AI</span>
        </Link>

        <div className="auth-brand-copy">
          <span className="eyebrow eyebrow--light">PRIVATE INFRASTRUCTURE WORKSPACE</span>
          <h1>Recover DNS with evidence, not guesswork.</h1>
          <p>Monitor protected domains, investigate DNS drift and approve deterministic recovery plans.</p>
          <div className="auth-proof-grid">
            <div><span className="auth-proof-label">RECOVERY MODEL</span><strong>Human approved</strong></div>
            <div><span className="auth-proof-label">INCIDENT ANALYSIS</span><strong>Evidence based</strong></div>
            <div><span className="auth-proof-label">DOMAIN OPERATIONS</span><strong>name.com API</strong></div>
          </div>
        </div>

        <div className="auth-brand-footer"><span className="auth-status-dot" /><span>DomainTwin infrastructure console</span></div>
      </section>

      <section className="auth-form-panel">
        <div className="auth-form-wrap">
          <Link className="auth-back" href="/">← Back to public site</Link>
          <div className="auth-form-heading">
            <span className="eyebrow">SECURE ACCESS</span>
            <h2>Sign in to DomainTwin</h2>
            <p>Use your DomainTwin account. Authentication uses a server-side Django session and CSRF-protected requests.</p>
          </div>

          <form className="auth-form" aria-label="Sign in form" onSubmit={handleSubmit}>
            <label>
              <span>Email or username</span>
              <input
                type="text"
                name="identifier"
                placeholder="you@company.com"
                autoComplete="username"
                value={identifier}
                onChange={(event) => setIdentifier(event.target.value)}
                required
              />
            </label>
            <label>
              <span>Password</span>
              <input
                type="password"
                name="password"
                placeholder="••••••••••••"
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
              />
            </label>
            <div className="auth-form-meta">
              <label className="auth-checkbox">
                <input
                  type="checkbox"
                  name="remember"
                  checked={remember}
                  onChange={(event) => setRemember(event.target.checked)}
                />
                <span>Keep me signed in</span>
              </label>
              <span className="auth-muted-link">Password reset arrives in a later productization checkpoint.</span>
            </div>
            <button className="button button--primary auth-submit" type="submit" disabled={loading}>
              {loading ? "Signing in…" : "Sign in"}
            </button>
          </form>

          {error ? (
            <div className="auth-notice" role="alert">
              <strong>Sign-in failed.</strong>
              <span>{error}</span>
            </div>
          ) : null}

          <div className="auth-notice">
            <strong>P2 identity boundary is active.</strong>
            <span>The private workspace will be placed behind this authenticated session boundary in the next checkpoint before RBAC is applied to recovery operations.</span>
          </div>

          <div className="auth-divider"><span>Public path</span></div>
          <div className="auth-form" style={{ gap: 10 }}>
            <Link className="button button--secondary auth-demo-button" href="/demo">Launch guided public demo</Link>
          </div>
          <p className="auth-security-note">Provider and AI secrets remain server-side and are never sent to the browser.</p>
        </div>
      </section>
    </main>
  );
}
