import Link from "next/link";
import { ApiStatus } from "@/components/ApiStatus";

const githubUrl = "https://github.com/topassky3/domaintwin-ai";

export default function Home() {
  return (
    <main>
      <header className="public-nav">
        <div className="shell nav-inner">
          <Link className="brand" href="/" aria-label="DomainTwin AI home">
            <span className="brand-mark">D</span>
            <span>DomainTwin AI</span>
          </Link>
          <nav className="nav-links" aria-label="Main navigation">
            <a href="#how-it-works">How it works</a>
            <a href="#why-domaintwin">Why DomainTwin</a>
            <a href="#security">Security</a>
            <a href={githubUrl} target="_blank" rel="noreferrer">GitHub</a>
          </nav>
          <div className="nav-actions">
            <Link className="button button--ghost" href="/login">Sign in</Link>
            <Link className="button button--primary" href="/demo">Launch Demo</Link>
          </div>
        </div>
      </header>

      <section className="hero shell">
        <div className="hero-copy">
          <span className="eyebrow">DNS CONTINUITY &amp; RECOVERY</span>
          <h1>DNS incidents don&apos;t need to become outages.</h1>
          <p className="hero-lead">Detect dangerous DNS changes, understand what broke, and restore a verified configuration in one click.</p>
          <div className="hero-actions">
            <Link className="button button--primary button--large" href="/demo">Launch Demo</Link>
            <a className="button button--secondary button--large" href={githubUrl} target="_blank" rel="noreferrer">View on GitHub</a>
          </div>
          <div className="integration-note"><span className="integration-icon">API</span>Powered by the <strong>name.com Domain API</strong></div>
        </div>

        <div className="incident-console" aria-label="Domain incident recovery example">
          <div className="console-header"><div><span className="console-label">LIVE INCIDENT STORY</span><strong>acme.com</strong></div><span className="environment-pill">PRODUCTION</span></div>
          <div className="state-row state-row--healthy"><div><span className="state-kicker">BEFORE</span><strong>HEALTHY</strong></div><div className="state-metrics"><span>Risk <b>5/100</b></span><span>HTTP <b>200 OK</b></span></div></div>
          <div className="event-line"><span className="event-node">1</span><div><strong>DNS A record changed</strong><code>203.0.113.10 → 198.51.100.77</code></div></div>
          <div className="state-row state-row--critical"><div><span className="state-kicker">INCIDENT</span><strong>CRITICAL</strong></div><div className="state-metrics"><span>Risk <b>90/100</b></span><span>HTTP <b>FAILED</b></span></div></div>
          <div className="analysis-card"><span className="analysis-badge">ROOT CAUSE FOUND</span><p>A production A record changed 43 seconds before HTTP availability was lost.</p><div className="evidence-row"><span>Deterministic evidence</span><strong>94% confidence</strong></div></div>
          <div className="recovery-strip"><span>Human approved recovery</span><strong>name.com → rollback</strong></div>
          <div className="state-row state-row--recovered"><div><span className="state-kicker">AFTER</span><strong>RECOVERED</strong></div><div className="state-metrics"><span>Risk <b>5/100</b></span><span>HTTP <b>200 OK</b></span></div></div>
        </div>
      </section>

      <section className="section section--soft" id="how-it-works"><div className="shell"><div className="section-heading"><span className="eyebrow">HOW IT WORKS</span><h2>From dangerous DNS drift to verified recovery.</h2><p>DomainTwin keeps the recovery path understandable, deterministic and auditable.</p></div><div className="workflow-grid">{[["01","Detect","Continuously compare live DNS state against verified snapshots."],["02","Explain","Correlate DNS changes with service health and generate evidence-based incident analysis."],["03","Recover","Preview deterministic rollback operations before making any production change."],["04","Verify","Confirm actual DNS state and service availability after recovery."]].map(([number,title,text]) => (<article className="workflow-card" key={number}><span className="workflow-number">{number}</span><h3>{title}</h3><p>{text}</p></article>))}</div></div></section>

      <section className="section shell"><div className="comparison-grid"><article className="comparison-card comparison-card--before"><span className="eyebrow eyebrow--critical">WITHOUT RECOVERY CONTEXT</span><h2>Before DomainTwin</h2><ul><li>DNS changed</li><li>HTTP failed</li><li>No clear root cause</li><li>Manual investigation</li><li>Unknown previous configuration</li></ul><div className="risk-banner risk-banner--critical"><span>CRITICAL</span><strong>90/100</strong></div></article><div className="comparison-arrow" aria-hidden="true">→</div><article className="comparison-card comparison-card--after"><span className="eyebrow eyebrow--success">VERIFIED CONTINUITY</span><h2>With DomainTwin</h2><ul><li>DNS drift detected</li><li>Root cause identified</li><li>Known-good snapshot available</li><li>Human-approved rollback</li><li>Recovery verified</li></ul><div className="risk-banner risk-banner--healthy"><span>HEALTHY</span><strong>5/100</strong></div></article></div></section>

      <section className="section section--navy" id="why-domaintwin"><div className="shell"><div className="section-heading section-heading--dark"><span className="eyebrow eyebrow--light">WHY DOMAINTWIN</span><h2>Infrastructure recovery that does not ask you to trust a black box.</h2></div><div className="value-grid"><article><span className="value-icon">01</span><h3>Deterministic first</h3><p>Critical operations are driven by DNS state, health checks and explicit rules — not LLM guesses.</p></article><article id="security"><span className="value-icon">02</span><h3>Human approved</h3><p>AI explains incidents, but humans approve every destructive production DNS operation.</p></article><article><span className="value-icon">03</span><h3>Auditable</h3><p>Snapshots, differences, recovery plans and verification steps produce a replayable incident timeline.</p></article></div></div></section>

      <section className="section shell"><div className="integration-panel"><div><span className="eyebrow">CORE INTEGRATION</span><h2>Domain operations are part of the recovery workflow.</h2><p>DomainTwin uses name.com as infrastructure, not decoration: domain state and DNS operations are central to the product.</p></div><div className="api-flow"><div className="api-flow-row"><span>Read domains</span><i>→</i><span>Read DNS</span><i>→</i><span>Detect drift</span><i>→</i><span>Restore records</span></div><div className="api-flow-row api-flow-row--muted"><span>Search domain</span><i>→</i><span>Availability</span><i>→</i><span>Register</span><i>→</i><span>Clone DNS</span></div></div></div></section>

      <section className="section shell"><div className="final-cta"><span className="eyebrow eyebrow--light">HACKATHON DEMO</span><h2>Break it. Detect it. Recover it.</h2><p>See DomainTwin take a domain from a dangerous DNS change to a verified recovery.</p><div className="hero-actions hero-actions--centered"><Link className="button button--light button--large" href="/demo">Launch Live Demo</Link><a className="button button--outline-light button--large" href={githubUrl} target="_blank" rel="noreferrer">View Source</a></div></div></section>

      <footer className="footer"><div className="shell footer-grid"><div><Link className="brand brand--dark" href="/"><span className="brand-mark">D</span><span>DomainTwin AI</span></Link><p>DNS continuity for teams that cannot afford to guess.</p><ApiStatus /></div><div className="footer-links"><a href={githubUrl} target="_blank" rel="noreferrer">GitHub</a><a href="https://api-cloud-ai-hackathon-2026.devpost.com/" target="_blank" rel="noreferrer">DevNetwork Hackathon</a><a href="#security">Security</a><Link href="/login">Sign in</Link></div></div><div className="shell footer-bottom">Built for DevNetwork [API + Cloud + AI] Hackathon 2026.</div></footer>
    </main>
  );
}
