"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  AIAnalysis,
  api,
  compactFingerprint,
  DiffChange,
  DiffResponse,
  DnsRecord,
  DomainsResponse,
  domainNameOf,
  encodeDomain,
  EvaluationResponse,
  formatDate,
  Incident,
  MonitorStatus,
  NameComStatus,
  RecordsResponse,
  RecoveryOperation,
  RecoveryPlan,
  Snapshot,
  SnapshotsResponse,
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
      .then((payload) => {
        if (!cancelled) setData(payload);
      })
      .catch((reason) => {
        if (!cancelled) setError(reason instanceof Error ? reason.message : "Request failed");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [path, version]);

  return { data, error, loading, reload: () => setVersion((value) => value + 1) };
}

function PageHeading({ eyebrow, title, copy, actions }: { eyebrow: string; title: string; copy: string; actions?: React.ReactNode }) {
  return (
    <div className="product-page-heading">
      <div>
        <span className="eyebrow">{eyebrow}</span>
        <h1>{title}</h1>
        <p>{copy}</p>
      </div>
      {actions ? <div className="product-heading-actions">{actions}</div> : null}
    </div>
  );
}

function LoadingState({ label = "Loading live DomainTwin state…" }: { label?: string }) {
  return <div className="product-state-panel"><span className="product-spinner" /> <strong>{label}</strong></div>;
}

function ErrorState({ message, retry }: { message: string; retry?: () => void }) {
  return (
    <div className="product-state-panel product-state-panel--error">
      <div><strong>External call failed</strong><p>{message}</p></div>
      {retry ? <button className="button button--secondary" onClick={retry} type="button">Retry</button> : null}
    </div>
  );
}

function EmptyState({ title, copy }: { title: string; copy: string }) {
  return <div className="product-empty"><strong>{title}</strong><p>{copy}</p></div>;
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

function recordText(record?: DnsRecord | null): string {
  if (!record) return "—";
  return `${record.type} ${record.host || "@"} → ${record.answer}`;
}

function operationSide(operation: RecoveryOperation, side: "before" | "after"): DnsRecord | null {
  if (side === "before") return operation.before ?? operation.current ?? null;
  return operation.after ?? operation.desired ?? null;
}

function DiffTable({ changes }: { changes: DiffChange[] }) {
  if (!changes.length) return <EmptyState title="No DNS changes" copy="The live configuration matches the selected baseline." />;
  return (
    <div className="product-table-wrap">
      <table className="product-table">
        <thead><tr><th>State</th><th>Record</th><th>Known-good</th><th>Current</th></tr></thead>
        <tbody>
          {changes.map((change, index) => {
            const record = change.after ?? change.before;
            return (
              <tr key={`${change.state}-${record?.type}-${record?.host}-${index}`}>
                <td><StateBadge state={change.state} /></td>
                <td><code>{record?.type ?? "—"} {record?.host || "@"}</code></td>
                <td><code>{change.before?.answer ?? "—"}</code></td>
                <td><code>{change.after?.answer ?? "—"}</code></td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function ProviderDepth() {
  const endpoints = ["LIST DOMAINS", "READ DNS", "DIFF", "SNAPSHOT", "UPDATE DNS", "VERIFY DNS"];
  return (
    <article className="product-card product-card--navy">
      <span className="product-card-kicker">NAME.COM INTEGRATION</span>
      <h3>Provider operations stay visible.</h3>
      <p>DomainTwin is not wrapping one decorative API call. Detection, rollback and verification all depend on provider state.</p>
      <div className="product-endpoint-stack">{endpoints.map((item) => <span key={item}>{item}</span>)}</div>
    </article>
  );
}

export function OverviewView() {
  const domains = useEndpoint<DomainsResponse>("namecom/domains/");
  const provider = useEndpoint<NameComStatus>("namecom/status/");
  const primaryDomain = domains.data?.domains.map(domainNameOf).find(Boolean) ?? null;
  const encoded = primaryDomain ? encodeDomain(primaryDomain) : null;
  const monitor = useEndpoint<MonitorStatus>(encoded ? `monitor/domains/${encoded}/status/` : null);
  const incidents = useEndpoint<{ incidents: Incident[]; totalCount: number }>(encoded ? `incidents/domains/${encoded}/` : null);
  const plans = useEndpoint<{ plans: RecoveryPlan[]; totalCount: number }>(encoded ? `recovery/domains/${encoded}/plans/` : null);

  if (domains.loading) return <><PageHeading eyebrow="CONTROL PLANE" title="Overview" copy="Live domain continuity state from the DomainTwin backend." /><LoadingState /></>;
  if (domains.error) return <><PageHeading eyebrow="CONTROL PLANE" title="Overview" copy="Live domain continuity state from the DomainTwin backend." /><ErrorState message={domains.error} retry={domains.reload} /></>;
  if (!primaryDomain) return <><PageHeading eyebrow="CONTROL PLANE" title="Overview" copy="Live domain continuity state from the DomainTwin backend." /><EmptyState title="No name.com domains found" copy="Connect a sandbox account with at least one domain to populate the private product UI." /></>;

  const latestIncident = monitor.data?.activeIncident ?? incidents.data?.incidents?.[0] ?? null;
  const latestPlan = plans.data?.plans?.[0] ?? null;
  const state = monitor.data?.state ?? "UNKNOWN";
  const risk = monitor.data?.activeIncident?.score ?? latestIncident?.score ?? 0;

  return (
    <>
      <PageHeading
        eyebrow="CONTROL PLANE"
        title="Domain continuity at a glance"
        copy="A judge should understand the protected domain, current state, risk and next action in seconds. Every value below comes from the live backend."
        actions={<Link className="button button--primary" href={`/app/domains/${encoded}`}>Open domain</Link>}
      />

      <section className={`product-hero-status product-hero-status--${state.toLowerCase()}`}>
        <div>
          <span className="product-card-kicker">PRIMARY DOMAIN</span>
          <h2>{primaryDomain}</h2>
          <p>{state === "INCIDENT" ? "A deterministic incident is active and requires operator attention." : state === "HEALTHY" ? "No active incident. Monitoring state is healthy." : "Domain is reachable in the control plane but currently degraded."}</p>
        </div>
        <div className="product-hero-score">
          <StateBadge state={state} />
          <strong>{risk}<small>/100 RISK</small></strong>
        </div>
      </section>

      <div className="product-metric-grid">
        <Metric label="PROVIDER" value={provider.data?.provider ?? "name.com"} hint={provider.data?.status ?? (provider.error ? "offline" : "checking")} />
        <Metric label="HEALTH" value={monitor.data?.latestHealth?.availabilityOk ? "AVAILABLE" : monitor.data?.latestHealth ? "FAILED" : "NO CHECK"} hint={formatDate(monitor.data?.latestHealth?.checkedAt)} />
        <Metric label="INCIDENTS" value={incidents.data?.totalCount ?? "—"} hint={latestIncident ? `${latestIncident.severity} latest` : "No history"} />
        <Metric label="RECOVERY" value={latestPlan?.status ?? "NO PLAN"} hint={latestPlan ? `${latestPlan.operationCount} operation(s)` : "Create preview when needed"} />
      </div>

      <div className="product-grid product-grid--2">
        <article className="product-card">
          <div className="product-card-head"><div><span className="product-card-kicker">LATEST INCIDENT</span><h3>{latestIncident ? `Incident #${latestIncident.id}` : "No incident recorded"}</h3></div>{latestIncident ? <StateBadge state={latestIncident.status} /> : null}</div>
          {latestIncident ? (
            <>
              <div className="product-risk-line"><strong>{latestIncident.score}/100</strong><StateBadge state={latestIncident.severity} /></div>
              <p>{latestIncident.factors?.[0]?.reason ?? "Deterministic evidence is available in the incident workspace."}</p>
              <Link className="product-text-link" href={`/app/incidents/${latestIncident.id}`}>Inspect evidence and AI explanation →</Link>
            </>
          ) : <p>Run a monitor evaluation from the domain workspace to establish incident state.</p>}
        </article>

        <article className="product-card">
          <div className="product-card-head"><div><span className="product-card-kicker">NEXT SAFE ACTION</span><h3>{latestPlan?.status === "PREVIEW" ? "Review rollback preview" : latestPlan?.status === "APPROVED" ? "Apply approved recovery" : "Inspect live DNS"}</h3></div>{latestPlan ? <StateBadge state={latestPlan.status} /> : null}</div>
          <p>Recovery is deterministic, approval-gated and verified against the known-good fingerprint before DomainTwin shows RECOVERED.</p>
          <div className="product-inline-actions">
            <Link className="button button--primary" href="/app/recovery">Recovery workspace</Link>
            <Link className="button button--secondary" href={`/app/domains/${encoded}/dns`}>View DNS diff</Link>
          </div>
        </article>
      </div>

      <div className="product-grid product-grid--2 product-grid--lower">
        <ProviderDepth />
        <article className="product-card">
          <span className="product-card-kicker">SAFETY CONTRACT</span>
          <h3>AI explains. Humans approve. DomainTwin verifies.</h3>
          <div className="product-safety-list">
            <span>✓ Deterministic risk score</span><span>✓ Evidence-grounded AI</span><span>✓ Explicit human approval</span><span>✓ Post-mutation verification</span>
          </div>
        </article>
      </div>
    </>
  );
}

export function DomainsView() {
  const domains = useEndpoint<DomainsResponse>("namecom/domains/");
  const [statuses, setStatuses] = useState<Record<string, MonitorStatus | null>>({});

  useEffect(() => {
    const names = domains.data?.domains.map(domainNameOf).filter(Boolean) ?? [];
    if (!names.length) return;
    let cancelled = false;
    Promise.all(names.map(async (name) => {
      try { return [name, await api<MonitorStatus>(`monitor/domains/${encodeDomain(name)}/status/`)] as const; }
      catch { return [name, null] as const; }
    })).then((rows) => { if (!cancelled) setStatuses(Object.fromEntries(rows)); });
    return () => { cancelled = true; };
  }, [domains.data]);

  return (
    <>
      <PageHeading eyebrow="DOMAIN PORTFOLIO" title="Protected domains" copy="Real domains returned by name.com. Open any domain to inspect monitoring, DNS, snapshots and recovery state." actions={<button className="button button--secondary" onClick={domains.reload} type="button">Refresh provider</button>} />
      {domains.loading ? <LoadingState label="Reading domains from name.com…" /> : domains.error ? <ErrorState message={domains.error} retry={domains.reload} /> : !domains.data?.domains.length ? <EmptyState title="No domains returned" copy="The connected name.com environment did not return domains." /> : (
        <div className="product-domain-grid">
          {domains.data.domains.map((domain) => {
            const name = domainNameOf(domain);
            const status = statuses[name];
            return (
              <article className="product-domain-card" key={name}>
                <div className="product-card-head"><span className="product-provider-tag">name.com</span><StateBadge state={status?.state ?? "UNKNOWN"} /></div>
                <h2>{name}</h2>
                <dl className="product-domain-meta">
                  <div><dt>Expires</dt><dd>{String(domain.expireDate ?? "—")}</dd></div>
                  <div><dt>Auto renew</dt><dd>{domain.autorenewEnabled === undefined ? "—" : domain.autorenewEnabled ? "ON" : "OFF"}</dd></div>
                  <div><dt>Availability</dt><dd>{status?.latestHealth?.availabilityOk ? "OK" : status?.latestHealth ? "FAILED" : "NO CHECK"}</dd></div>
                </dl>
                <div className="product-inline-actions"><Link className="button button--primary" href={`/app/domains/${encodeDomain(name)}`}>Open workspace</Link><Link className="button button--secondary" href={`/app/domains/${encodeDomain(name)}/dns`}>DNS</Link></div>
              </article>
            );
          })}
        </div>
      )}
    </>
  );
}

export function DomainDetailView({ domain }: { domain: string }) {
  const encoded = encodeDomain(domain);
  const detail = useEndpoint<{ environment: string; domain: Record<string, unknown> }>(`namecom/domains/${encoded}/`);
  const monitor = useEndpoint<MonitorStatus>(`monitor/domains/${encoded}/status/`);
  const incidents = useEndpoint<{ incidents: Incident[]; totalCount: number }>(`incidents/domains/${encoded}/`);
  const plans = useEndpoint<{ plans: RecoveryPlan[]; totalCount: number }>(`recovery/domains/${encoded}/plans/`);
  const [evaluating, setEvaluating] = useState(false);
  const [evaluation, setEvaluation] = useState<EvaluationResponse | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  async function evaluate() {
    setEvaluating(true); setActionError(null);
    try {
      const value = await api<EvaluationResponse>(`monitor/domains/${encoded}/evaluate/`, { method: "POST" });
      setEvaluation(value); monitor.reload(); incidents.reload();
    } catch (error) { setActionError(error instanceof Error ? error.message : "Evaluation failed"); }
    finally { setEvaluating(false); }
  }

  const activeIncident = evaluation?.incident ?? monitor.data?.activeIncident ?? incidents.data?.incidents?.[0] ?? null;
  const state = evaluation?.state ?? monitor.data?.state ?? "UNKNOWN";
  const score = evaluation?.risk.score ?? activeIncident?.score ?? 0;
  const severity = evaluation?.risk.severity ?? activeIncident?.severity ?? "LOW";
  const latestPlan = plans.data?.plans?.[0] ?? null;

  return (
    <>
      <PageHeading eyebrow="DOMAIN WORKSPACE" title={domain} copy="Monitor current provider state, run deterministic evaluation and move into DNS, snapshot or recovery workflows without leaving the protected domain." actions={<><button className="button button--primary" disabled={evaluating} onClick={evaluate} type="button">{evaluating ? "Evaluating…" : "Evaluate now"}</button><button className="button button--secondary" onClick={() => { detail.reload(); monitor.reload(); }} type="button">Refresh</button></>} />
      {actionError ? <ErrorState message={actionError} /> : null}
      {(detail.loading || monitor.loading) ? <LoadingState /> : detail.error ? <ErrorState message={detail.error} retry={detail.reload} /> : (
        <>
          <section className={`product-hero-status product-hero-status--${state.toLowerCase()}`}>
            <div><span className="product-card-kicker">CURRENT MONITOR STATE</span><h2>{domain}</h2><p>{activeIncident?.factors?.[0]?.reason ?? "No active deterministic incident factor is currently attached to this domain."}</p></div>
            <div className="product-hero-score"><StateBadge state={state} /><strong>{score}<small>/100 · {severity}</small></strong></div>
          </section>
          <div className="product-metric-grid">
            <Metric label="HTTP" value={(evaluation?.health ?? monitor.data?.latestHealth)?.http?.ok ? "OK" : (evaluation?.health ?? monitor.data?.latestHealth)?.http ? "FAILED" : "NO CHECK"} />
            <Metric label="HTTPS" value={(evaluation?.health ?? monitor.data?.latestHealth)?.https?.ok ? "OK" : (evaluation?.health ?? monitor.data?.latestHealth)?.https ? "FAILED" : "NO CHECK"} />
            <Metric label="INCIDENT" value={activeIncident ? `#${activeIncident.id}` : "NONE"} hint={activeIncident?.status} />
            <Metric label="RECOVERY" value={latestPlan?.status ?? "NO PLAN"} hint={latestPlan ? `${latestPlan.operationCount} ops` : undefined} />
          </div>
          <div className="product-grid product-grid--3">
            <Link className="product-action-card" href={`/app/domains/${encoded}/dns`}><span>DNS</span><h3>Live records + diff</h3><p>Read current name.com records and compare them to known-good.</p><b>Open DNS →</b></Link>
            <Link className="product-action-card" href={`/app/domains/${encoded}/snapshots`}><span>TWIN</span><h3>Snapshots</h3><p>Capture immutable DNS state and explicitly mark trusted baselines.</p><b>Open snapshots →</b></Link>
            <Link className="product-action-card" href={activeIncident ? `/app/incidents/${activeIncident.id}` : "/app/incidents"}><span>INC</span><h3>Incident evidence</h3><p>Inspect deterministic factors, timeline and evidence-based AI analysis.</p><b>Open incidents →</b></Link>
          </div>
          <div className="product-grid product-grid--2 product-grid--lower">
            <article className="product-card"><span className="product-card-kicker">PROVIDER OBJECT</span><h3>name.com domain metadata</h3><pre className="product-json-preview">{JSON.stringify(detail.data?.domain ?? {}, null, 2)}</pre></article>
            <article className="product-card"><span className="product-card-kicker">RECOVERY BOUNDARY</span><h3>Human-approved mutation only</h3><p>Creating a preview does not mutate DNS. The backend requires explicit approval and rechecks the live fingerprint before apply.</p><Link className="button button--primary" href="/app/recovery">Open recovery workspace</Link></article>
          </div>
        </>
      )}
    </>
  );
}

export function DnsView({ domain }: { domain: string }) {
  const encoded = encodeDomain(domain);
  const records = useEndpoint<RecordsResponse>(`namecom/domains/${encoded}/records/`);
  const diff = useEndpoint<DiffResponse>(`twin/domains/${encoded}/diff/`);
  return (
    <>
      <PageHeading eyebrow="LIVE DNS" title={`${domain} DNS`} copy="Current name.com records alongside the deterministic Current → Known-Good diff used by risk and recovery." actions={<button className="button button--secondary" onClick={() => { records.reload(); diff.reload(); }} type="button">Refresh live state</button>} />
      <div className="product-integration-banner"><span>name.com</span><code>GET /domains/{domain}/records</code><b>→ normalize → fingerprint → diff</b></div>
      <div className="product-grid product-grid--2">
        <article className="product-card"><div className="product-card-head"><div><span className="product-card-kicker">LIVE RECORDS</span><h3>Provider configuration</h3></div><span className="product-provider-tag">{records.data?.environment?.toUpperCase() ?? "…"}</span></div>{records.loading ? <LoadingState label="Reading name.com DNS…" /> : records.error ? <ErrorState message={records.error} retry={records.reload} /> : !records.data?.records.length ? <EmptyState title="No DNS records" copy="The provider returned an empty record set." /> : <div className="product-record-list">{records.data.records.map((record, index) => <div key={`${record.id ?? index}-${record.type}-${record.host}`}><span>{record.type}</span><code>{record.host || "@"}</code><strong>{record.answer}</strong><small>TTL {record.ttl ?? "—"}</small></div>)}</div>}</article>
        <article className="product-card"><div className="product-card-head"><div><span className="product-card-kicker">FINGERPRINT</span><h3>Known-good vs live</h3></div>{diff.data ? <StateBadge state={diff.data.driftDetected ? "DRIFT" : "HEALTHY"} /> : null}</div>{diff.loading ? <LoadingState label="Computing deterministic diff…" /> : diff.error ? <ErrorState message={diff.error} retry={diff.reload} /> : diff.data ? <><div className="product-fingerprint"><span>KNOWN-GOOD</span><code title={diff.data.baselineFingerprint}>{compactFingerprint(diff.data.baselineFingerprint)}</code><span>LIVE</span><code title={diff.data.liveFingerprint}>{compactFingerprint(diff.data.liveFingerprint)}</code></div><div className="product-summary-row">{["ADDED","REMOVED","MODIFIED","UNCHANGED"].map((key) => <div key={key}><span>{key}</span><strong>{diff.data?.summary?.[key] ?? 0}</strong></div>)}</div></> : null}</article>
      </div>
      <article className="product-card product-grid--lower"><div className="product-card-head"><div><span className="product-card-kicker">DETERMINISTIC DNS DIFF</span><h3>Before / after evidence</h3></div>{diff.data ? <span className="product-provider-tag">SNAPSHOT v{diff.data.baselineVersion}</span> : null}</div>{diff.data ? <DiffTable changes={diff.data.changes.filter((change) => change.state !== "UNCHANGED")} /> : diff.loading ? null : <EmptyState title="Diff unavailable" copy="A known-good snapshot is required before DomainTwin can calculate drift." />}</article>
    </>
  );
}

export function SnapshotsView({ domain }: { domain: string }) {
  const encoded = encodeDomain(domain);
  const snapshots = useEndpoint<SnapshotsResponse>(`twin/domains/${encoded}/snapshots/`);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function capture() {
    setBusy("capture"); setError(null);
    try { await api(`twin/domains/${encoded}/snapshots/`, { method: "POST" }); snapshots.reload(); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Snapshot failed"); }
    finally { setBusy(null); }
  }
  async function mark(snapshot: Snapshot) {
    setBusy(`mark-${snapshot.id}`); setError(null);
    try { await api(`twin/domains/${encoded}/snapshots/${snapshot.id}/known-good/`, { method: "POST" }); snapshots.reload(); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Mark known-good failed"); }
    finally { setBusy(null); }
  }

  return (
    <>
      <PageHeading eyebrow="DIGITAL TWIN" title={`${domain} snapshots`} copy="Immutable DNS snapshots make rollback explainable and verifiable. Trust is explicit: only an operator can mark a snapshot known-good." actions={<button className="button button--primary" disabled={busy === "capture"} onClick={capture} type="button">{busy === "capture" ? "Capturing…" : "Capture live snapshot"}</button>} />
      {error ? <ErrorState message={error} /> : null}
      {snapshots.loading ? <LoadingState /> : snapshots.error ? <ErrorState message={snapshots.error} retry={snapshots.reload} /> : !snapshots.data?.snapshots.length ? <EmptyState title="No snapshots yet" copy="Capture the current provider state to create version 1." /> : (
        <div className="product-snapshot-list">{snapshots.data.snapshots.map((snapshot) => <article className={snapshot.isKnownGood ? "product-snapshot is-known-good" : "product-snapshot"} key={snapshot.id}><div><span className="product-card-kicker">VERSION {snapshot.version}</span><h3>Snapshot #{snapshot.id}</h3><p>{snapshot.recordCount} normalized record(s) · {formatDate(snapshot.createdAt)}</p></div><div className="product-snapshot-fingerprint"><span>SHA256</span><code title={snapshot.fingerprint}>{compactFingerprint(snapshot.fingerprint)}</code></div><div>{snapshot.isKnownGood ? <span className="known-good-chip">KNOWN GOOD</span> : <button className="button button--secondary" disabled={busy === `mark-${snapshot.id}`} onClick={() => mark(snapshot)} type="button">Mark known-good</button>}</div></article>)}</div>
      )}
    </>
  );
}

export function IncidentsView() {
  const domains = useEndpoint<DomainsResponse>("namecom/domains/");
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const names = domains.data?.domains.map(domainNameOf).filter(Boolean) ?? [];
    if (!domains.data) return;
    if (!names.length) { setIncidents([]); setLoading(false); return; }
    let cancelled = false; setLoading(true); setError(null);
    Promise.all(names.map((name) => api<{ incidents: Incident[] }>(`incidents/domains/${encodeDomain(name)}/`)))
      .then((payloads) => { if (!cancelled) setIncidents(payloads.flatMap((payload) => payload.incidents).sort((a,b) => +new Date(b.openedAt) - +new Date(a.openedAt))); })
      .catch((reason) => { if (!cancelled) setError(reason instanceof Error ? reason.message : "Incident loading failed"); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [domains.data]);

  return (
    <>
      <PageHeading eyebrow="INCIDENT CENTER" title="Deterministic incident history" copy="Every incident exposes score, factors, evidence and timestamps. Open one to see the timeline, evidence-grounded AI and linked recovery state." />
      {(domains.loading || loading) ? <LoadingState label="Loading incident history…" /> : domains.error ? <ErrorState message={domains.error} retry={domains.reload} /> : error ? <ErrorState message={error} /> : !incidents.length ? <EmptyState title="No incidents recorded" copy="No domain in the connected environment has incident history yet." /> : (
        <div className="product-table-wrap"><table className="product-table"><thead><tr><th>Incident</th><th>Domain</th><th>Status</th><th>Severity</th><th>Risk</th><th>Opened</th><th /></tr></thead><tbody>{incidents.map((incident) => <tr key={incident.id}><td><strong>#{incident.id}</strong></td><td><code>{incident.domainName}</code></td><td><StateBadge state={incident.status} /></td><td><StateBadge state={incident.severity} /></td><td><strong>{incident.score}/100</strong></td><td>{formatDate(incident.openedAt)}</td><td><Link className="product-text-link" href={`/app/incidents/${incident.id}`}>Inspect →</Link></td></tr>)}</tbody></table></div>
      )}
    </>
  );
}

export function IncidentDetailView({ incidentId }: { incidentId: number }) {
  const incident = useEndpoint<{ incident: Incident }>(`incidents/${incidentId}/`);
  const explanation = useEndpoint<{ analysis: AIAnalysis }>(`ai/incidents/${incidentId}/explanation/`);
  const domain = incident.data?.incident.domainName ?? null;
  const encoded = domain ? encodeDomain(domain) : null;
  const plans = useEndpoint<{ plans: RecoveryPlan[] }>(encoded ? `recovery/domains/${encoded}/plans/` : null);
  const [generating, setGenerating] = useState(false);
  const [aiAction, setAiAction] = useState<AIAnalysis | null>(null);
  const [aiError, setAiError] = useState<string | null>(null);

  async function generate() {
    setGenerating(true); setAiError(null);
    try { const response = await api<{ analysis: AIAnalysis }>(`ai/incidents/${incidentId}/explanation/`, { method: "POST" }); setAiAction(response.analysis); explanation.reload(); }
    catch (reason) { setAiError(reason instanceof Error ? reason.message : "AI request failed"); }
    finally { setGenerating(false); }
  }

  if (incident.loading) return <><PageHeading eyebrow="INCIDENT EVIDENCE" title={`Incident #${incidentId}`} copy="Loading deterministic incident evidence." /><LoadingState /></>;
  if (incident.error || !incident.data) return <><PageHeading eyebrow="INCIDENT EVIDENCE" title={`Incident #${incidentId}`} copy="Deterministic incident evidence." /><ErrorState message={incident.error ?? "Incident not found"} retry={incident.reload} /></>;

  const row = incident.data.incident;
  const ai = aiAction ?? explanation.data?.analysis ?? null;
  const linkedPlan = plans.data?.plans.find((plan) => plan.incidentId === row.id) ?? null;

  return (
    <>
      <PageHeading eyebrow="INCIDENT EVIDENCE" title={`Incident #${row.id}`} copy={`${row.domainName} · opened ${formatDate(row.openedAt)}. Facts remain deterministic; probable cause is explicitly separated as AI inference.`} actions={<><StateBadge state={row.status} /><Link className="button button--secondary" href={`/app/domains/${encodeDomain(row.domainName)}`}>Domain</Link></>} />
      <section className="product-incident-banner"><div><span>RISK</span><strong>{row.score}/100</strong></div><div><span>SEVERITY</span><StateBadge state={row.severity} /></div><div><span>EVIDENCE</span><strong>{row.factorCount} factor(s)</strong></div><div><span>RECOVERY</span><strong>{linkedPlan?.status ?? "NO PLAN"}</strong></div></section>

      <div className="product-grid product-grid--2">
        <article className="product-card"><span className="product-card-kicker">DETERMINISTIC FACTORS</span><h3>Why the score exists</h3><div className="product-factor-list">{row.factors.map((factor, index) => <div key={`${factor.ruleId}-${index}`}><span>+{factor.points ?? 0}</span><div><strong>{factor.ruleId ?? "RULE"}</strong><p>{factor.reason ?? "No reason supplied"}</p>{factor.before || factor.after ? <code>{recordText(factor.before)} → {recordText(factor.after)}</code> : null}</div></div>)}</div></article>
        <article className="product-card product-ai-card"><div className="product-card-head"><div><span className="product-card-kicker">EVIDENCE-BASED AI ANALYSIS</span><h3>{ai?.status === "GENERATED" ? "Probable cause" : "AI explanation"}</h3></div>{ai ? <StateBadge state={ai.status} /> : null}</div>{explanation.loading ? <LoadingState label="Reading persisted AI analysis…" /> : aiError ? <ErrorState message={aiError} /> : ai?.status === "GENERATED" ? <><blockquote>{ai.probableCause}</blockquote><div className="product-ai-meta"><span>Affected service <strong>{ai.affectedService}</strong></span><span>Confidence <strong>{ai.confidence?.level ?? "—"}</strong></span><span>{ai.cached ? "CACHED" : "FRESH"} · {ai.model}</span></div><p className="product-ai-recommendation"><strong>Recommended action:</strong> {ai.recommendedAction}</p><div className="product-evidence-chips">{ai.evidence?.map((item) => <span title={item.fact} key={item.id}>{item.id}</span>)}</div></> : <><p>{ai?.error ?? "No generated AI explanation is stored for this evidence fingerprint."}</p><button className="button button--primary" disabled={generating} onClick={generate} type="button">{generating ? "Generating…" : "Generate explanation"}</button><small className="product-ai-safety">AI cannot mutate DNS. If the provider is unavailable, deterministic evidence and recovery remain usable.</small></>}</article>
      </div>

      <article className="product-card product-grid--lower"><div className="product-card-head"><div><span className="product-card-kicker">INCIDENT TIMELINE</span><h3>Ordered audit evidence</h3></div><span className="product-provider-tag">{row.timeline?.length ?? 0} EVENTS</span></div>{!row.timeline?.length ? <EmptyState title="No timeline events" copy="This incident does not currently expose timeline events." /> : <div className="product-timeline">{row.timeline.map((event) => <div key={`${event.sequence}-${event.eventType}`}><span>{event.sequence}</span><div><strong>{event.eventType.replaceAll("_", " ")}</strong><p>{formatDate(event.occurredAt)}</p></div></div>)}</div>}</article>
      {linkedPlan ? <article className="product-card product-grid--lower"><div className="product-card-head"><div><span className="product-card-kicker">LINKED RECOVERY</span><h3>Plan #{linkedPlan.id}</h3></div><StateBadge state={linkedPlan.status} /></div><p>{linkedPlan.operationCount} deterministic operation(s) target snapshot v{linkedPlan.baselineVersion}.</p><Link className="button button--primary" href="/app/recovery">Open recovery workspace</Link></article> : null}
    </>
  );
}

function RecoveryOperations({ plan }: { plan: RecoveryPlan }) {
  if (!plan.operations.length) return <EmptyState title="No mutation required" copy="Current DNS already matches the known-good target." />;
  return <div className="product-table-wrap"><table className="product-table"><thead><tr><th>Action</th><th>Record</th><th>Current</th><th>Restore</th></tr></thead><tbody>{plan.operations.map((operation, index) => { const before = operationSide(operation, "before"); const after = operationSide(operation, "after"); const record = after ?? before; return <tr key={`${operation.action}-${index}`}><td><StateBadge state={operation.action} /></td><td><code>{record?.type ?? "—"} {record?.host || "@"}</code></td><td><code>{before?.answer ?? "—"}</code></td><td><code>{after?.answer ?? "—"}</code></td></tr>; })}</tbody></table></div>;
}

export function RecoveryView() {
  const provider = useEndpoint<NameComStatus>("namecom/status/");
  const domains = useEndpoint<DomainsResponse>("namecom/domains/");
  const names = useMemo(() => domains.data?.domains.map(domainNameOf).filter(Boolean) ?? [], [domains.data]);
  const [selectedDomain, setSelectedDomain] = useState("");
  const [plans, setPlans] = useState<RecoveryPlan[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => { if (!selectedDomain && names.length) setSelectedDomain(names[0]); }, [names, selectedDomain]);
  useEffect(() => {
    if (!names.length) { if (domains.data) setLoaded(true); return; }
    let cancelled = false; setLoaded(false);
    Promise.all(names.map((name) => api<{ plans: RecoveryPlan[] }>(`recovery/domains/${encodeDomain(name)}/plans/`)))
      .then((responses) => { if (!cancelled) setPlans(responses.flatMap((response) => response.plans).sort((a,b) => +new Date(b.createdAt) - +new Date(a.createdAt))); })
      .catch((reason) => { if (!cancelled) setError(reason instanceof Error ? reason.message : "Recovery plans failed"); })
      .finally(() => { if (!cancelled) setLoaded(true); });
    return () => { cancelled = true; };
  }, [names, domains.data]);

  const activePlan = plans.find((plan) => plan.domainName === selectedDomain) ?? null;
  function upsert(plan: RecoveryPlan) { setPlans((current) => [plan, ...current.filter((item) => item.id !== plan.id)]); }

  async function createPreview() {
    if (!selectedDomain) return;
    setBusy("preview"); setError(null);
    try { const response = await api<{ plan: RecoveryPlan }>(`recovery/domains/${encodeDomain(selectedDomain)}/plans/`, { method: "POST" }); upsert(response.plan); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Preview failed"); }
    finally { setBusy(null); }
  }
  async function approve() {
    if (!activePlan) return;
    setBusy("approve"); setError(null);
    try { const response = await api<{ plan: RecoveryPlan }>(`recovery/plans/${activePlan.id}/approve/`, { method: "POST", body: JSON.stringify({ approve: true }) }); upsert(response.plan); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Approval failed"); }
    finally { setBusy(null); }
  }
  async function apply() {
    if (!activePlan) return;
    setBusy("apply"); setError(null);
    try { const response = await api<{ plan: RecoveryPlan }>(`recovery/plans/${activePlan.id}/apply/`, { method: "POST" }); upsert(response.plan); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Recovery apply failed"); }
    finally { setBusy(null); }
  }

  const environment = provider.data?.environment?.toUpperCase() ?? "UNKNOWN";
  const verified = activePlan?.verification as { matched?: boolean; expectedFingerprint?: string; actualFingerprint?: string } | undefined;

  return (
    <>
      <PageHeading eyebrow="RECOVERY CONTROL" title="Verified recovery workspace" copy="Preview exact Current → Known-Good operations, require explicit approval, mutate through name.com and independently verify the resulting fingerprint." actions={<span className={environment === "PRODUCTION" ? "product-env product-env--production product-env--large" : "product-env product-env--sandbox product-env--large"}>{environment}</span>} />
      <div className="product-recovery-safety"><strong>Human approval boundary</strong><span>Preview never mutates DNS. Apply remains blocked by the backend until approval and mutation guards allow it.</span></div>
      {error ? <ErrorState message={error} /> : null}
      {(domains.loading || !loaded) ? <LoadingState label="Loading recovery state…" /> : domains.error ? <ErrorState message={domains.error} retry={domains.reload} /> : !names.length ? <EmptyState title="No domains available" copy="Recovery needs a connected name.com domain and a known-good snapshot." /> : (
        <>
          <div className="product-recovery-toolbar">
            <label><span>DOMAIN</span><select value={selectedDomain} onChange={(event) => setSelectedDomain(event.target.value)}>{names.map((name) => <option key={name} value={name}>{name}</option>)}</select></label>
            <button className="button button--secondary" disabled={busy === "preview"} onClick={createPreview} type="button">{busy === "preview" ? "Planning…" : activePlan ? "Re-check / create preview" : "Create rollback preview"}</button>
            {activePlan?.requiresApproval ? <button className="button button--primary" disabled={busy === "approve"} onClick={approve} type="button">{busy === "approve" ? "Approving…" : "Approve recovery"}</button> : null}
            {activePlan?.canApply ? <button className="button button--danger" disabled={busy === "apply"} onClick={apply} type="button">{busy === "apply" ? "Applying + verifying…" : "Apply approved recovery"}</button> : null}
          </div>

          {!activePlan ? <EmptyState title="No recovery plan for this domain" copy="Create a rollback preview. DomainTwin will read live name.com DNS and compare it with the known-good snapshot without mutating anything." /> : (
            <>
              <section className={`product-recovery-status product-recovery-status--${activePlan.status.toLowerCase()}`}>
                <div><span className="product-card-kicker">PLAN #{activePlan.id}</span><h2>{activePlan.status}</h2><p>{activePlan.operationCount} operation(s) · target snapshot v{activePlan.baselineVersion}</p></div>
                <div><StateBadge state={activePlan.status} /><code>{compactFingerprint(activePlan.planFingerprint)}</code></div>
              </section>
              <article className="product-card product-grid--lower"><div className="product-card-head"><div><span className="product-card-kicker">ROLLBACK PREVIEW</span><h3>Exact name.com operations</h3></div><span className="product-provider-tag">{activePlan.operationCount} OPS</span></div><RecoveryOperations plan={activePlan} /></article>
              <div className="product-grid product-grid--2 product-grid--lower">
                <article className="product-card"><span className="product-card-kicker">VERIFICATION</span><h3>{activePlan.status === "RECOVERED" ? "Expected equals actual" : "Post-mutation proof"}</h3><div className="product-verification-grid"><div><span>EXPECTED</span><code>{compactFingerprint(activePlan.targetFingerprint)}</code></div><div><span>ACTUAL</span><code>{compactFingerprint(verified?.actualFingerprint)}</code></div><div><span>MATCH</span><strong>{verified?.matched === true ? "YES" : verified?.matched === false ? "NO" : "PENDING"}</strong></div></div></article>
                <article className="product-card"><span className="product-card-kicker">AUDIT TRAIL</span><h3>Recovery events</h3>{!activePlan.audit?.length ? <p>Open or mutate this plan to populate detailed audit events.</p> : <div className="product-mini-timeline">{activePlan.audit.map((event) => <div key={`${event.sequence}-${event.eventType}`}><span>{event.sequence}</span><strong>{event.eventType.replaceAll("_", " ")}</strong><small>{formatDate(event.occurredAt)}</small></div>)}</div>}</article>
              </div>
              {activePlan.incidentId ? <div className="product-follow-link"><span>Linked incident #{activePlan.incidentId}</span><Link href={`/app/incidents/${activePlan.incidentId}`}>Inspect evidence →</Link></div> : null}
            </>
          )}
        </>
      )}
    </>
  );
}
