import Link from "next/link";
import { ApiStatus } from "@/components/ApiStatus";

const steps = [
  ["01", "Healthy baseline", "Known-good DNS snapshot verified and HTTP service available."],
  ["02", "Dangerous drift", "Production A record changes to an unknown destination."],
  ["03", "Incident intelligence", "DomainTwin correlates DNS drift with HTTP failure and explains the evidence."],
  ["04", "Human-approved recovery", "The operator reviews the exact rollback plan before any DNS mutation."],
  ["05", "Verified recovery", "Expected and actual DNS match and the recovery is independently verified."],
];

export default function DemoPage() {
  return (
    <main className="demo-page">
      <header className="demo-topbar">
        <div className="shell demo-topbar-inner">
          <Link className="brand" href="/" aria-label="DomainTwin AI home"><span className="brand-mark">D</span><span>DomainTwin AI</span></Link>
          <div className="demo-mode-badge"><span /> HACKATHON DEMO</div>
          <div className="demo-topbar-actions"><ApiStatus /><Link className="button button--secondary" href="/">Exit demo</Link></div>
        </div>
      </header>

      <section className="demo-hero shell">
        <div className="demo-hero-copy">
          <span className="eyebrow">GUIDED INCIDENT RECOVERY</span>
          <h1>Watch a DNS incident go from broken to verified recovery.</h1>
          <p>This safe, public scenario demonstrates the exact DomainTwin story judges need to understand: detect the dangerous change, explain the evidence, preview the rollback, require human approval and prove recovery.</p>
          <div className="hero-actions"><a className="button button--primary button--large" href="#scenario">Start walkthrough</a><Link className="button button--secondary button--large" href="/app/overview">Open live workspace</Link></div>
        </div>
        <aside className="demo-briefing"><div className="demo-briefing-head"><div><span className="console-label">SCENARIO</span><strong>Production DNS outage</strong></div><span className="environment-pill">SAFE DEMO</span></div><dl><div><dt>Domain</dt><dd>acme.com</dd></div><div><dt>Provider</dt><dd>name.com</dd></div><div><dt>Known-good</dt><dd>Available</dd></div><div><dt>Initial risk</dt><dd className="demo-good">5/100</dd></div><div><dt>Incident risk</dt><dd className="demo-bad">90/100</dd></div><div><dt>Target outcome</dt><dd className="demo-good">RECOVERED</dd></div></dl></aside>
      </section>

      <section className="demo-workspace" id="scenario"><div className="shell">
        <div className="demo-workspace-header"><div><span className="eyebrow">DEMO WORKSPACE</span><h2>Incident INC-2026-08-17-001</h2></div><div className="demo-workspace-status"><span className="demo-critical-dot" /> CRITICAL · 90/100</div></div>
        <div className="demo-layout"><div className="demo-main-column">
          <article className="demo-card demo-card--critical"><div className="demo-card-head"><div><span className="console-label">DETECTED DRIFT</span><h3>A record changed before service failure</h3></div><span className="risk-chip risk-chip--critical">+30 RISK</span></div><div className="demo-diff-row"><div><span>KNOWN-GOOD</span><code>203.0.113.10</code></div><strong>→</strong><div><span>CURRENT</span><code>198.51.100.77</code></div></div><div className="demo-health-row"><span>HTTP</span><strong className="demo-bad">FAILED</strong><span>HTTPS</span><strong className="demo-bad">FAILED</strong><span>DNS</span><strong className="demo-good">RESOLVES</strong></div></article>
          <article className="demo-card"><div className="demo-card-head"><div><span className="console-label">AI ROOT CAUSE ANALYSIS</span><h3>Evidence-based explanation</h3></div><span className="confidence-chip">94% confidence</span></div><blockquote>“The production A record changed before HTTP and HTTPS availability was lost. The destination differs from the last known-good configuration.”</blockquote><div className="demo-evidence-list"><div><span>14:38:11</span><strong>A record modified</strong></div><div><span>14:38:54</span><strong>HTTP health check failed</strong></div><div><span>14:38:56</span><strong>HTTPS health check failed</strong></div><div><span>14:39:02</span><strong>Critical incident created</strong></div></div><p className="demo-ai-rule">AI explains evidence. It does not autonomously modify DNS.</p></article>
          <article className="demo-card"><div className="demo-card-head"><div><span className="console-label">ROLLBACK PREVIEW</span><h3>Restore the last known-good DNS state</h3></div><span className="environment-pill">HUMAN APPROVAL</span></div><div className="demo-operation-table"><div className="demo-operation-row demo-operation-head"><span>Action</span><span>Record</span><span>Current</span><span>Restore</span></div><div className="demo-operation-row"><b className="demo-update">UPDATE</b><code>A @</code><code>198.51.100.77</code><code>203.0.113.10</code></div><div className="demo-operation-row"><b className="demo-create">CREATE</b><code>MX @</code><code>—</code><code>mail.acme.com</code></div><div className="demo-operation-row"><b className="demo-update">UPDATE</b><code>TXT _dmarc</code><code>p=none</code><code>p=reject</code></div><div className="demo-operation-row"><b className="demo-delete">DELETE</b><code>CNAME temp</code><code>unknown.example.net</code><code>—</code></div></div><div className="demo-approval-strip"><div><span className="auth-status-dot" /><span>Known-good snapshot verified · name.com connected · deterministic plan ready</span></div><button className="button button--primary" type="button" disabled>Confirm recovery — demo only</button></div></article>
          <article className="demo-card demo-card--success"><div className="demo-card-head"><div><span className="console-label">VERIFIED OUTCOME</span><h3>Internet presence restored</h3></div><span className="risk-chip risk-chip--healthy">RECOVERED</span></div><div className="demo-outcome-grid"><div><span>RISK</span><strong><em>90</em> → 5</strong></div><div><span>DNS MATCH</span><strong>100%</strong></div><div><span>HTTP</span><strong>200 OK</strong></div><div><span>RECOVERY</span><strong>27 sec</strong></div></div></article>
        </div><aside className="demo-sidebar"><div className="demo-sidebar-card"><span className="console-label">WALKTHROUGH</span><div className="demo-step-list">{steps.map(([number,title,text]) => <div className="demo-step" key={number}><span>{number}</span><div><strong>{title}</strong><p>{text}</p></div></div>)}</div></div><div className="demo-sidebar-card demo-sidebar-card--namecom"><span className="console-label">WHY NAME.COM IS CENTRAL</span><h3>Real domain operations, not a decorative API call.</h3><div className="demo-api-stack"><span>Read domains</span><span>Read DNS</span><span>Restore DNS</span><span>Search domains</span><span>Check availability</span><span>Register + clone</span></div></div></aside></div>
      </div></section>

      <section className="demo-next shell"><span className="eyebrow">LIVE PRODUCT WORKSPACE</span><h2>The guided story is now wired to the real DomainTwin control plane.</h2><p>The private workspace reads configured name.com state, incidents, snapshots, evidence-based AI analysis and the verified recovery engine through a server-side proxy.</p><div className="hero-actions hero-actions--centered"><Link className="button button--primary button--large" href="/app/overview">Open live workspace</Link><Link className="button button--secondary button--large" href="/login">View access boundary</Link></div></section>
    </main>
  );
}
