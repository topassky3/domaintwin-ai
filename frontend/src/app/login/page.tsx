import Link from "next/link";

export default function LoginPage() {
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
            <p>Authentication is intentionally deferred until the hackathon recovery flow is complete.</p>
          </div>

          <form className="auth-form" aria-label="Sign in form">
            <label><span>Email</span><input type="email" name="email" placeholder="you@company.com" autoComplete="email" /></label>
            <label><span>Password</span><input type="password" name="password" placeholder="••••••••••••" autoComplete="current-password" /></label>
            <div className="auth-form-meta"><label className="auth-checkbox"><input type="checkbox" name="remember" /><span>Keep me signed in</span></label><span className="auth-muted-link">Forgot password?</span></div>
            <button className="button button--primary auth-submit" type="button" disabled>Sign in</button>
          </form>

          <div className="auth-notice">
            <strong>Hackathon evaluator access is enabled without account creation.</strong>
            <span>The live workspace uses configured local/sandbox provider credentials. Public registration remains intentionally out of scope for Gate 7.</span>
          </div>

          <div className="auth-divider"><span>Evaluator paths</span></div>
          <div className="auth-form" style={{ gap: 10 }}>
            <Link className="button button--primary auth-demo-button" href="/app/overview">Open live sandbox workspace</Link>
            <Link className="button button--secondary auth-demo-button" href="/demo">Launch guided public demo</Link>
          </div>
          <p className="auth-security-note">Provider and AI secrets remain server-side and are never sent to the browser.</p>
        </div>
      </section>
    </main>
  );
}
