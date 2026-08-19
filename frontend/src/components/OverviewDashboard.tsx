"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  api,
  DomainsResponse,
  domainNameOf,
  encodeDomain,
  formatDate,
  Incident,
  MonitorStatus,
  NameComStatus,
  RecoveryPlan,
} from "@/lib/domaintwin";

type LoadState<T> = { data: T | null; error: string | null; loading: boolean; reload: () => void };

function useEndpoint<T>(path: string | null): LoadState<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(Boolean(path));
  const [version, setVersion] = useState(0);

  useEffect(() => {
    if (!path) {
      setLoading(false);
      setData(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    api<T>(path)
      .then((payload) => { if (!cancelled) setData(payload); })
      .catch((reason) => { if (!cancelled) setError(reason instanceof Error ? reason.message : "Request failed"); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [path, version]);

  return { data, error, loading, reload: () => setVersion((value) => value + 1) };
}

function StateBadge({ state }: { state?: string | null }) {
  const normalized = (state ?? "UNKNOWN").toUpperCase();
  const tone = normalized === "HEALTHY" || normalized === "RECOVERED" || normalized === "RESOLVED"
    ? "success"
    : normalized === "INCIDENT" || normalized === "CRITICAL" || normalized === "FAILED" || normalized === "PARTIAL"
      ? "critical"
      : normalized === "DEGRADED" || normalized === "HIGH" || normalized === "MEDIUM" || normalized === "STALE"
        ? "warning"
        : "neutral";
  return <span className={`product-state-badge product-state-badge--${tone}`}>{normalized}</span>;
}

function Metric({ label, value, hint }: { label: string; value: React.ReactNode; hint?: string }) {
  return <div className="product-metric"><span>{label}</span><strong>{value}</strong>{hint ? <small>{hint}</small> : null}</div>;
}

function LoadingState() {
  return <div className="product-state-panel"><span className="product-spinner" /> <strong>Loading live DomainTwin state…</strong></div>;
}

function ErrorState({ message, retry }: { message: string; retry: () => void }) {
  return <div className="product-state-panel product-state-panel--error"><div><strong>External call failed</strong><p>{message}</p></div><button className="button button--secondary" onClick={retry} type="button">Retry</button></div>;
}

export function OverviewDashboard() {
  const domains = useEndpoint<DomainsResponse>("namecom/domains/");
  const provider = useEndpoint<NameComStatus>("namecom/status/");
  const primaryDomain = domains.data?.domains.map(domainNameOf).find(Boolean) ?? null;
  const encoded = primaryDomain ? encodeDomain(primaryDomain) : null;
  const monitor = useEndpoint<MonitorStatus>(encoded ? `monitor/domains/${encoded}/status/` : null);
  const incidents = useEndpoint<{ incidents: Incident[]; totalCount: number }>(encoded ? `incidents/domains/${encoded}/` : null);
  const plans = useEndpoint<{ plans: RecoveryPlan[]; totalCount: number }>(encoded ? `recovery/domains/${encoded}/plans/` : null);

  if (domains.loading) return <><div className="product-page-heading"><div><span className="eyebrow">CONTROL PLANE</span><h1>Domain continuity at a glance</h1><p>Live domain continuity state from the DomainTwin backend.</p></div></div><LoadingState /></>;
  if (domains.error) return <><div className="product-page-heading"><div><span className="eyebrow">CONTROL PLANE</span><h1>Domain continuity at a glance</h1><p>Live domain continuity state from the DomainTwin backend.</p></div></div><ErrorState message={domains.error} retry={domains.reload} /></>;
  if (!primaryDomain || !encoded) return <div className="product-empty"><strong>No name.com domains found</strong><p>Connect a sandbox account with at least one domain to populate the control plane.</p></div>;

  const activeIncident = monitor.data?.activeIncident ?? null;
  const latestIncident = activeIncident ?? incidents.data?.incidents?.[0] ?? null;
  const latestPlan = plans.data?.plans?.[0] ?? null;
  const state = monitor.data?.state ?? "UNKNOWN";
  const dnsRecovered = latestPlan?.status === "RECOVERED";
  const availabilityFailed = monitor.data?.latestHealth ? !monitor.data.latestHealth.availabilityOk : false;

  const statusCopy = state === "INCIDENT"
    ? "A deterministic incident is active and requires operator attention."
    : state === "HEALTHY"
      ? "No active incident. Current monitoring state is healthy."
      : dnsRecovered && availabilityFailed
        ? "DNS recovery is verified. External availability remains degraded in the sandbox environment."
        : state === "DEGRADED"
          ? "No active incident, but the latest external health observation is degraded."
          : "Current state is being established from live backend evidence.";

  return (
    <>
      <div className="product-page-heading">
        <div>
          <span className="eyebrow">CONTROL PLANE</span>
          <h1>Domain continuity at a glance</h1>
          <p>Current operational state is separated from historical incident risk so recovery status is unambiguous.</p>
        </div>
        <div className="product-heading-actions"><Link className="button button--primary" href={`/app/domains/${encoded}`}>Open domain</Link></div>
      </div>

      <section className={`product-hero-status product-hero-status--${state.toLowerCase()}`}>
        <div>
          <span className="product-card-kicker">PRIMARY DOMAIN</span>
          <h2>{primaryDomain}</h2>
          <p>{statusCopy}</p>
        </div>
        <div className="product-hero-score">
          <StateBadge state={state} />
          {activeIncident ? (
            <strong>{activeIncident.score}<small>/100 ACTIVE RISK</small></strong>
          ) : (
            <strong>—<small>NO ACTIVE INCIDENT RISK</small></strong>
          )}
        </div>
      </section>

      <div className="product-metric-grid">
        <Metric label="PROVIDER" value={provider.data?.provider ?? "name.com"} hint={provider.data?.status ?? (provider.error ? "offline" : "checking")} />
        <Metric label="CURRENT HEALTH" value={monitor.data?.latestHealth?.availabilityOk ? "AVAILABLE" : monitor.data?.latestHealth ? "FAILED" : "NO CHECK"} hint={formatDate(monitor.data?.latestHealth?.checkedAt)} />
        <Metric label="LATEST INCIDENT RISK" value={latestIncident ? `${latestIncident.score}/100` : "NONE"} hint={latestIncident ? `${latestIncident.severity} · ${latestIncident.status}` : "No incident history"} />
        <Metric label="DNS RECOVERY" value={latestPlan?.status ?? "NO PLAN"} hint={latestPlan ? `${latestPlan.operationCount} operation(s)` : "No recovery history"} />
      </div>

      <div className="product-grid product-grid--2">
        <article className="product-card">
          <div className="product-card-head"><div><span className="product-card-kicker">LATEST INCIDENT · HISTORICAL</span><h3>{latestIncident ? `Incident #${latestIncident.id}` : "No incident recorded"}</h3></div>{latestIncident ? <StateBadge state={latestIncident.status} /> : null}</div>
          {latestIncident ? <><div className="product-risk-line"><strong>{latestIncident.score}/100</strong><StateBadge state={latestIncident.severity} /></div><p>{latestIncident.factors?.[0]?.reason ?? "Deterministic evidence is available in the incident workspace."}</p><Link className="product-text-link" href={`/app/incidents/${latestIncident.id}`}>Inspect evidence and AI explanation →</Link></> : <p>Run a monitor evaluation from the domain workspace to establish incident history.</p>}
        </article>

        <article className="product-card">
          <div className="product-card-head"><div><span className="product-card-kicker">CURRENT RECOVERY STATE</span><h3>{dnsRecovered ? "DNS restored and verified" : latestPlan?.status === "PREVIEW" ? "Review rollback preview" : latestPlan?.status === "APPROVED" ? "Apply approved recovery" : "Inspect live DNS"}</h3></div>{latestPlan ? <StateBadge state={latestPlan.status} /> : null}</div>
          <p>{dnsRecovered ? "Expected and actual DNS fingerprints matched after the provider mutation. External health is tracked independently." : "Recovery is deterministic, approval-gated and verified against the known-good fingerprint before DomainTwin shows RECOVERED."}</p>
          <div className="product-inline-actions"><Link className="button button--primary" href="/app/recovery">Recovery workspace</Link><Link className="button button--secondary" href={`/app/domains/${encoded}/dns`}>View DNS diff</Link></div>
        </article>
      </div>

      <div className="product-grid product-grid--2 product-grid--lower">
        <article className="product-card product-card--navy"><span className="product-card-kicker">NAME.COM INTEGRATION</span><h3>Provider operations stay visible.</h3><p>Detection, rollback and verification all depend on provider state.</p><div className="product-endpoint-stack"><span>LIST DOMAINS</span><span>READ DNS</span><span>DIFF</span><span>SNAPSHOT</span><span>UPDATE DNS</span><span>VERIFY DNS</span></div></article>
        <article className="product-card"><span className="product-card-kicker">SAFETY CONTRACT</span><h3>AI explains. Humans approve. DomainTwin verifies.</h3><div className="product-safety-list"><span>✓ Deterministic risk score</span><span>✓ Evidence-grounded AI</span><span>✓ Explicit human approval</span><span>✓ Post-mutation verification</span></div></article>
      </div>
    </>
  );
}
