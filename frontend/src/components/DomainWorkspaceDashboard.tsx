"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  api,
  encodeDomain,
  EvaluationResponse,
  formatDate,
  Incident,
  MonitorStatus,
  RecoveryPlan,
} from "@/lib/domaintwin";

type LoadState<T> = { data: T | null; error: string | null; loading: boolean; reload: () => void };

type SafeDomain = {
  domainName?: string;
  createDate?: string;
  expireDate?: string;
  autorenewEnabled?: boolean;
  locked?: boolean;
  locks?: string[];
  transferLockExpiresAt?: string;
  privacyEnabled?: boolean;
  nameservers?: string[];
  renewalPrice?: number;
};

function useEndpoint<T>(path: string): LoadState<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [version, setVersion] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    api<T>(path)
      .then((value) => { if (!cancelled) setData(value); })
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

export function DomainWorkspaceDashboard({ domain }: { domain: string }) {
  const encoded = encodeDomain(domain);
  const detail = useEndpoint<{ environment: string; domain: SafeDomain }>(`namecom/domains/${encoded}/`);
  const monitor = useEndpoint<MonitorStatus>(`monitor/domains/${encoded}/status/`);
  const incidents = useEndpoint<{ incidents: Incident[]; totalCount: number }>(`incidents/domains/${encoded}/`);
  const plans = useEndpoint<{ plans: RecoveryPlan[]; totalCount: number }>(`recovery/domains/${encoded}/plans/`);
  const [evaluation, setEvaluation] = useState<EvaluationResponse | null>(null);
  const [evaluating, setEvaluating] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  async function evaluate() {
    setEvaluating(true);
    setActionError(null);
    try {
      const value = await api<EvaluationResponse>(`monitor/domains/${encoded}/evaluate/`, { method: "POST" });
      setEvaluation(value);
      monitor.reload();
      incidents.reload();
      plans.reload();
    } catch (error) {
      setActionError(error instanceof Error ? error.message : "Evaluation failed");
    } finally {
      setEvaluating(false);
    }
  }

  const activeIncident = evaluation?.incident ?? monitor.data?.activeIncident ?? null;
  const latestIncident = activeIncident ?? incidents.data?.incidents?.[0] ?? null;
  const latestPlan = plans.data?.plans?.[0] ?? null;
  const activeIncidentPlan = activeIncident
    ? plans.data?.plans?.find((plan) => plan.incidentId === activeIncident.id) ?? null
    : null;
  const displayedPlan = activeIncident ? activeIncidentPlan : latestPlan;
  const state = evaluation?.state ?? monitor.data?.state ?? "UNKNOWN";
  const evaluationRisk = evaluation?.risk ?? null;
  const currentRiskScore = evaluationRisk?.score ?? activeIncident?.score ?? null;
  const currentRiskSeverity = evaluationRisk?.severity ?? activeIncident?.severity ?? null;
  const recovered = !activeIncident && latestPlan?.status === "RECOVERED";
  const healthFailed = monitor.data?.latestHealth ? !monitor.data.latestHealth.availabilityOk : false;

  const stateCopy = state === "INCIDENT"
    ? "An active deterministic incident requires operator attention."
    : recovered && healthFailed
      ? "DNS recovery is verified. External availability remains degraded independently in the sandbox environment."
      : state === "DEGRADED"
        ? "No active incident is open, but the latest external health observation is degraded."
        : state === "HEALTHY"
          ? "Current monitoring state is healthy and no incident is open."
          : "Current operational state is being established from backend evidence.";

  const recoveryValue = displayedPlan?.status ?? (activeIncident ? "NO PLAN YET" : "NO PLAN");
  const recoveryHint = displayedPlan
    ? `${displayedPlan.operationCount} operation(s)${activeIncident ? ` · incident #${activeIncident.id}` : ""}`
    : activeIncident
      ? `Create a preview for incident #${activeIncident.id}`
      : "No recovery history";

  return (
    <>
      <div className="product-page-heading">
        <div>
          <span className="eyebrow">DOMAIN WORKSPACE</span>
          <h1>{domain}</h1>
          <p>Monitor provider state, inspect continuity evidence and enter recovery workflows without exposing registrant contact data to the browser.</p>
        </div>
        <div className="product-heading-actions">
          <button className="button button--primary" type="button" onClick={evaluate} disabled={evaluating}>{evaluating ? "Evaluating…" : "Evaluate now"}</button>
          <button className="button button--secondary" type="button" onClick={() => { detail.reload(); monitor.reload(); incidents.reload(); plans.reload(); }}>Refresh</button>
        </div>
      </div>

      {actionError ? <div className="product-state-panel product-state-panel--error"><div><strong>Evaluation failed</strong><p>{actionError}</p></div></div> : null}

      <section className={`product-hero-status product-hero-status--${state.toLowerCase()}`}>
        <div>
          <span className="product-card-kicker">CURRENT MONITOR STATE</span>
          <h2>{domain}</h2>
          <p>{stateCopy}</p>
        </div>
        <div className="product-hero-score">
          <StateBadge state={state} />
          {currentRiskScore !== null ? <strong>{currentRiskScore}<small>/100 · {currentRiskSeverity ?? "RISK"}</small></strong> : <strong>—<small>NO ACTIVE INCIDENT RISK</small></strong>}
        </div>
      </section>

      <div className="product-metric-grid">
        <Metric label="HTTP" value={monitor.data?.latestHealth?.http?.ok ? "OK" : monitor.data?.latestHealth ? "FAILED" : "NO CHECK"} />
        <Metric label="HTTPS" value={monitor.data?.latestHealth?.https?.ok ? "OK" : monitor.data?.latestHealth ? "FAILED" : "NO CHECK"} />
        <Metric label="ACTIVE INCIDENT" value={activeIncident ? `#${activeIncident.id}` : "NONE"} hint={activeIncident ? activeIncident.severity : latestIncident ? `Latest #${latestIncident.id} · ${latestIncident.status}` : "No history"} />
        <Metric label={activeIncident ? "INCIDENT RECOVERY" : "DNS RECOVERY"} value={recoveryValue} hint={recoveryHint} />
      </div>

      <div className="product-grid product-grid--3">
        <article className="product-card"><span className="product-card-kicker">DNS</span><h3>Live records + diff</h3><p>Read current name.com records and compare them to the trusted known-good baseline.</p><Link className="product-text-link" href={`/app/domains/${encoded}/dns`}>Open DNS →</Link></article>
        <article className="product-card"><span className="product-card-kicker">TWIN</span><h3>Snapshots</h3><p>Capture immutable DNS state and explicitly identify trusted known-good baselines.</p><Link className="product-text-link" href={`/app/domains/${encoded}/snapshots`}>Open snapshots →</Link></article>
        <article className="product-card"><span className="product-card-kicker">INCIDENTS</span><h3>{latestIncident ? `Latest #${latestIncident.id} · ${latestIncident.status}` : "Incident evidence"}</h3><p>{latestIncident ? `${latestIncident.score}/100 ${latestIncident.severity} is historical unless an incident is OPEN.` : "Inspect deterministic factors, timeline and evidence-based AI analysis."}</p><Link className="product-text-link" href={latestIncident ? `/app/incidents/${latestIncident.id}` : "/app/incidents"}>Open incidents →</Link></article>
      </div>

      <div className="product-grid product-grid--2 product-grid--lower">
        <article className="product-card">
          <span className="product-card-kicker">PROVIDER METADATA · SAFE VIEW</span>
          <h3>Operational name.com domain metadata</h3>
          {detail.loading ? <p>Reading provider metadata…</p> : detail.error ? <p>{detail.error}</p> : (
            <dl className="product-domain-meta">
              <div><dt>Created</dt><dd>{formatDate(detail.data?.domain.createDate)}</dd></div>
              <div><dt>Expires</dt><dd>{formatDate(detail.data?.domain.expireDate)}</dd></div>
              <div><dt>Auto renew</dt><dd>{detail.data?.domain.autorenewEnabled ? "ON" : "OFF"}</dd></div>
              <div><dt>Registrar lock</dt><dd>{detail.data?.domain.locked ? "ON" : "OFF"}</dd></div>
              <div><dt>Privacy</dt><dd>{detail.data?.domain.privacyEnabled ? "ENABLED" : "DISABLED"}</dd></div>
              <div><dt>Renewal price</dt><dd>{detail.data?.domain.renewalPrice !== undefined ? `$${detail.data.domain.renewalPrice}` : "—"}</dd></div>
            </dl>
          )}
          <p className="product-muted">Registrant, admin, billing and technical contacts are intentionally removed by the backend before this response reaches the browser.</p>
          {detail.data?.domain.nameservers?.length ? <div className="product-endpoint-stack">{detail.data.domain.nameservers.map((value) => <span key={value}>{value}</span>)}</div> : null}
        </article>

        <article className="product-card">
          <span className="product-card-kicker">RECOVERY BOUNDARY</span>
          <h3>Human-approved mutation only</h3>
          <p>Creating a preview does not mutate DNS. The backend requires explicit approval and rechecks provider state before apply.</p>
          <div className="product-inline-actions"><Link className="button button--primary" href="/app/recovery">Open recovery workspace</Link>{displayedPlan ? <StateBadge state={displayedPlan.status} /> : null}</div>
        </article>
      </div>
    </>
  );
}
