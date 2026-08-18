import Link from "next/link";

export default function LoginPage() {
  return (
    <main className="login-shell">
      <Link className="brand brand--dark" href="/">
        <span className="brand-mark">D</span>
        <span>DomainTwin AI</span>
      </Link>

      <section className="login-card">
        <span className="eyebrow">PRIVATE WORKSPACE</span>
        <h1>Sign in</h1>
        <p>The authenticated DomainTwin workspace will be enabled in the next implementation phase.</p>
        <Link className="button button--primary" href="/">
          Back to public site
        </Link>
      </section>
    </main>
  );
}
