import Link from "next/link";

const judgeAnswers = [
  ["01", "Who pays?", "Agencies, MSPs, DevOps/platform teams and technical freelancers managing multiple business-critical domains."],
  ["02", "What do they avoid?", "DNS incidents that break websites, APIs or email — plus slow, uncertain recovery under pressure."],
  ["03", "Why DomainTwin?", "Known-good snapshots, deterministic rollback, human approval, provider execution, fresh re-read and fingerprint proof."],
  ["04", "Why name.com?", "name.com is the execution plane for domain discovery, DNS read/write, emergency search/check/register and clone verification."],
  ["05", "What becomes SaaS?", "Scheduled monitoring, team workspaces, alerts, recovery policies, audit retention, portfolio plans and billing."],
];

const roadmap = [
  ["PHASE 1", "Operable SaaS", "Accounts, organizations, encrypted credentials, scheduled monitoring, alerts, production deployment and billing."],
  ["PHASE 2", "Team continuity", "RBAC, approval roles, recovery reports, retention controls, portfolio dashboards and MSP segmentation."],
  ["PHASE 3", "Continuity platform", "Emergency readiness policies, richer lifecycle automation, API/policy-as-code and additional registrar adapters where useful."],
];

export default function FeasibilityPage() {
  return (
    <main>
      <header className="public-nav">
        <div className="shell nav-inner">
          <Link className="brand" href="/" aria-label="DomainTwin AI home">
            <span className="brand-mark">D</span><span>DomainTwin AI</span>
          </Link>
          <div className="nav-links">
            <Link href="/demo">Technical demo</Link>
            <Link href="/app/overview">Live workspace</Link>
          </div>
          <div className="nav-actions">
            <Link className="button button--secondary" href="/demo">View demo</Link>
          </div>
        </div>
      </header>

      <section className="section">
        <div className="shell">
          <div className="section-heading">
            <span className="eyebrow">GATE 10 · STARTUP FEASIBILITY</span>
            <h2>A domain-continuity product a judge can understand in 30 seconds.</h2>
            <p>DomainTwin is not another DNS editor. It is a verified recovery control plane for teams responsible for business-critical domains.</p>
          </div>

          <div className="workflow-grid">
            {judgeAnswers.slice(0, 4).map(([number, title, text]) => (
              <article className="workflow-card" key={number}>
                <span className="workflow-number">{number}</span>
                <h3>{title}</h3>
                <p>{text}</p>
              </article>
            ))}
          </div>

          <div className="comparison-card" style={{ marginTop: 18 }}>
            <span className="workflow-number">05</span>
            <h2>{judgeAnswers[4][1]}</h2>
            <p style={{ color: "var(--muted)", lineHeight: 1.7 }}>{judgeAnswers[4][2]}</p>
          </div>
        </div>
      </section>

      <section className="section section--navy">
        <div className="shell">
          <div className="section-heading section-heading--dark">
            <span className="eyebrow eyebrow--light">THE PAID PROBLEM</span>
            <h2>Reduce DNS incident uncertainty, not just DNS editing time.</h2>
            <p>The customer pays for a repeatable recovery boundary: detect drift, understand evidence, approve an exact plan, restore through the provider and prove the intended state is back.</p>
          </div>
          <div className="value-grid">
            <article><span className="value-icon">MTTD</span><h3>Detect drift sooner</h3><p>Compare live name.com DNS against a trusted known-good twin and correlate changes with health failures.</p></article>
            <article><span className="value-icon">MTTR</span><h3>Recover deliberately</h3><p>Preview exact CREATE / UPDATE / DELETE operations before a human-approved provider mutation.</p></article>
            <article><span className="value-icon">PROOF</span><h3>Verify the outcome</h3><p>Re-read the provider and require expected and actual normalized DNS fingerprints to match before success.</p></article>
          </div>
        </div>
      </section>

      <section className="section section--soft">
        <div className="shell">
          <div className="integration-panel">
            <div>
              <span className="eyebrow">WHY NAME.COM IS CENTRAL</span>
              <h2>DomainTwin needs a real execution plane.</h2>
              <p>Detection alone is not the product. name.com provides the domain and DNS lifecycle needed to complete recovery and emergency continuity.</p>
            </div>
            <div className="api-flow">
              <div className="api-flow-row"><span>List domains</span><i>→</i><span>Read DNS</span><i>→</i><span>Restore DNS</span><i>→</i><span>Verify</span></div>
              <div className="api-flow-row"><span>Search</span><i>→</i><span>Check</span><i>→</i><span>Register</span><i>→</i><span>Clone</span><i>→</i><span>Verify</span></div>
              <div className="api-flow-row api-flow-row--muted"><span>Server-side credentials</span><span>Human approval</span><span>Sandbox / production guards</span></div>
            </div>
          </div>
        </div>
      </section>

      <section className="section">
        <div className="shell">
          <div className="section-heading">
            <span className="eyebrow">BUSINESS MODEL HYPOTHESIS</span>
            <h2>Recurring protection, packaged by managed portfolio.</h2>
            <p>This is a hackathon business-model hypothesis, not validated pricing. The commercial structure is a recurring subscription with domain/portfolio limits and higher tiers for collaboration, retention, reporting and automation.</p>
          </div>
          <div className="value-grid" style={{ color: "white", background: "var(--navy)", borderRadius: 14, padding: 18 }}>
            <article><span className="value-icon">STARTER</span><h3>Small portfolio</h3><p>Snapshots, drift monitoring, incident history and verified human-approved recovery.</p></article>
            <article><span className="value-icon">TEAM</span><h3>Shared operations</h3><p>Larger portfolios, approval workflows, longer audit retention, alerts and recovery policy controls.</p></article>
            <article><span className="value-icon">MSP</span><h3>Customer portfolios</h3><p>Client segmentation, higher limits, reusable policy templates, reports and API/webhook automation.</p></article>
          </div>
        </div>
      </section>

      <section className="section section--soft">
        <div className="shell">
          <div className="section-heading">
            <span className="eyebrow">POST-HACKATHON ROADMAP</span>
            <h2>The difficult domain-specific engine already exists; SaaS plumbing comes next.</h2>
            <p>Gate 10 deliberately separates proven recovery technology from the standard multi-tenant capabilities still required for a commercial product.</p>
          </div>
          <div className="value-grid">
            {roadmap.map(([phase, title, text]) => (
              <article style={{ color: "white", background: "var(--navy)" }} key={phase}>
                <span className="value-icon">{phase}</span><h3>{title}</h3><p>{text}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="section">
        <div className="shell">
          <div className="final-cta">
            <span className="eyebrow eyebrow--light">JUDGE-READY SUMMARY</span>
            <h2>Verified continuity for teams that cannot afford to guess during a DNS incident.</h2>
            <p>Known-good twin → deterministic evidence → human-approved name.com recovery → fresh provider verification → auditable proof.</p>
            <div className="hero-actions hero-actions--centered">
              <Link className="button button--light button--large" href="/demo">See the incident demo</Link>
              <Link className="button button--outline-light button--large" href="/app/overview">Open the live control plane</Link>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
