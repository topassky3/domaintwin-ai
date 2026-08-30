import Link from "next/link";
import { ApiStatus } from "@/components/ApiStatus";

const steps = [
  ["01", "Trusted baseline", "Known-good snapshot v3 stores the exact DNS state that recovery must restore."],
  ["02", "Controlled drift", "The Name.com Sandbox A record changes from 203.0.113.10 to 198.51.100.77."],
  ["03", "Incident #8", "DomainTwin detects the drift and scores the incident CRITICAL at 75/100 using deterministic factors."],
  ["04", "Recovery #8", "The operator reviews one exact UPDATE operation and explicitly approves recovery."],
  ["05", "Proof", "DomainTwin re-reads Name.com and marks RECOVERED only when expected and actual fingerprints match."],
];

export default function DemoPage() {
  return (
    <main className="demo-page">
      <header className="demo-topbar">
        <div className="shell demo-topbar-inner">
          <Link className="brand" href="/" aria-label="DomainTwin AI home"><span className="brand-mark">D</span><span>DomainTwin AI</span></Link>
          <div className="demo-mode-badge"><span /> VERIFIED HACKATHON DEMO</div>
          <div className="demo-topbar-actions"><ApiStatus /><Link className="button button--secondary" href="/">Exit demo</Link></div>
        </div>
      </header>

      <section className="demo-hero shell">
        <div className="demo-hero-copy">
          <span className="eyebrow">REAL NAME.COM SANDBOX RECOVERY</span>
          <h1>From DNS drift to independently verified recovery.</h1>
          <p>This walkthrough mirrors the recovery that was actually executed and preserved in the live DomainTwin workspace: detect the drift, score the evidence, preview one deterministic rollback, require human approval, execute through Name.com Sandbox and prove the provider matches the trusted snapshot.</p>
          <div className="hero-actions"><a className="button button--primary button--large" href="#scenario">View verified recovery</a><Link className="button button--secondary button--large" href="/app/overview">Open live workspace</Link></div>
        </div>
        <aside className="demo-briefing"><div className="demo-briefing-head"><div><span className="console-label">VALIDATED CASE</span><strong>Incident #8 / Recovery #8</strong></div><span className="environment-pill">NAME.COM SANDBOX</span></div><dl><div><dt>Domain</dt><dd>domaintwin-gate1-20260818151419.com</dd></div><div><dt>Provider</dt><dd>Name.com Sandbox</dd></div><div><dt>Known-good</dt><dd>Snapshot v3</dd></div><div><dt>Incident risk</dt><dd className="demo-bad">75/100</dd></div><div><dt>Recovery</dt><dd className="demo-good">RECOVERED</dd></div><div><dt>Verification</dt><dd className="demo-good">MATCH YES</dd></div></dl></aside>
      </section>

      <section className="demo-workspace" id="scenario"><div className="shell">
        <div className="demo-workspace-header"><div><span className="eyebrow">PERSISTED RECOVERY EVIDENCE</span><h2>Incident #8</h2></div><div className="demo-workspace-status"><span className="demo-critical-dot" /> CRITICAL · 75/100</div></div>
        <div className="demo-layout"><div className="demo-main-column">
          <article className="demo-card demo-card--critical"><div className="demo-card-head"><div><span className="console-label">DETECTED DRIFT</span><h3>A www no longer matched the trusted snapshot</h3></div><span className="risk-chip risk-chip--critical">75/100</span></div><div className="demo-diff-row"><div><span>KNOWN-GOOD</span><code>203.0.113.10</code></div><strong>→</strong><div><span>OBSERVED</span><code>198.51.100.77</code></div></div><div className="demo-health-row"><span>DNS DRIFT</span><strong className="demo-bad">DETECTED</strong><span>HTTP</span><strong className="demo-bad">FAILED</strong><span>INCIDENT</span><strong className="demo-bad">CREATED</strong></div></article>

          <article className="demo-card"><div className="demo-card-head"><div><span className="console-label">DETERMINISTIC INCIDENT EVIDENCE</span><h3>Why DomainTwin scored the incident CRITICAL</h3></div><span className="confidence-chip">EXPLICIT FACTORS</span></div><div className="demo-evidence-list"><div><span>+30</span><strong>ADDRESS_RECORD_CHANGED</strong></div><div><span>+30</span><strong>HTTP_HEALTH_FAILED</strong></div><div><span>+15</span><strong>UNKNOWN_DESTINATION</strong></div><div><span>=75</span><strong>CRITICAL incident score</strong></div></div><p className="demo-ai-rule">The core decision is deterministic. The optional AI layer may explain evidence, but it never controls DNS authority.</p></article>

          <article className="demo-card"><div className="demo-card-head"><div><span className="console-label">RECOVERY PLAN #8</span><h3>One exact rollback operation</h3></div><span className="environment-pill">HUMAN APPROVED</span></div><div className="demo-operation-table"><div className="demo-operation-row demo-operation-head"><span>Action</span><span>Record</span><span>Current</span><span>Restore</span></div><div className="demo-operation-row"><b className="demo-update">UPDATE</b><code>A www</code><code>198.51.100.77</code><code>203.0.113.10</code></div></div><div className="demo-approval-strip"><div><span className="auth-status-dot" /><span>Known-good snapshot v3 · exact preview · explicit approval · Name.com Sandbox execution</span></div><button className="button button--primary" type="button" disabled>Historical recovery — read only</button></div></article>

          <article className="demo-card demo-card--success"><div className="demo-card-head"><div><span className="console-label">PROVIDER VERIFICATION</span><h3>Recovery #8 is proven by a fresh Name.com read</h3></div><span className="risk-chip risk-chip--healthy">RECOVERED</span></div><div className="demo-outcome-grid"><div><span>EXPECTED</span><strong>a3b35ae640…dad54313</strong></div><div><span>ACTUAL</span><strong>a3b35ae640…dad54313</strong></div><div><span>FINGERPRINT</span><strong>MATCH YES</strong></div><div><span>DNS DRIFT</span><strong>FALSE</strong></div></div><p className="demo-ai-rule">Post-recovery monitoring remains DEGRADED at 30/100 because this sandbox domain has no real HTTP service. DNS itself is restored, verified and no new incident is created.</p></article>
        </div><aside className="demo-sidebar"><div className="demo-sidebar-card"><span className="console-label">VERIFIED WALKTHROUGH</span><div className="demo-step-list">{steps.map(([number,title,text]) => <div className="demo-step" key={number}><span>{number}</span><div><strong>{title}</strong><p>{text}</p></div></div>)}</div></div><div className="demo-sidebar-card demo-sidebar-card--namecom"><span className="console-label">WHY NAME.COM IS CENTRAL</span><h3>Provider execution plus provider verification.</h3><div className="demo-api-stack"><span>Read domains</span><span>Read DNS</span><span>Restore DNS</span><span>Search domains</span><span>Check availability</span><span>Register + clone</span></div></div></aside></div>
      </div></section>

      <section className="demo-next shell"><span className="eyebrow">LIVE PRODUCT WORKSPACE</span><h2>Inspect the same Incident #8 and Recovery #8 in the deployed control plane.</h2><p>The public judge account is intentionally read-only. Continuous monitoring remains active, while DNS mutation and emergency registration permissions stay disabled in the public deployment.</p><div className="hero-actions hero-actions--centered"><Link className="button button--primary button--large" href="/app/overview">Open live workspace</Link><Link className="button button--secondary button--large" href="/login">Judge login</Link></div></section>
    </main>
  );
}
