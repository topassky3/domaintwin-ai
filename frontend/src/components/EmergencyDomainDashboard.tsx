"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  api,
  compactFingerprint,
  DomainsResponse,
  domainNameOf,
  EmergencyDomainPlan,
  EmergencySearchResponse,
  EmergencySearchResult,
  EmergencyStatus,
  encodeDomain,
  formatDate,
} from "@/lib/domaintwin";

type LoadState<T> = {
  data: T | null;
  error: string | null;
  loading: boolean;
  reload: () => void;
};

function useEndpoint<T>(path: string | null): LoadState<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(Boolean(path));
  const [version, setVersion] = useState(0);

  useEffect(() => {
    if (!path) {
      setData(null);
      setError(null);
      setLoading(false);
      return;
    }
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
  const tone = normalized === "READY" || normalized === "AVAILABLE" || normalized === "VERIFIED"
    ? "success"
    : normalized === "FAILED" || normalized === "PARTIAL" || normalized === "STALE" || normalized === "BLOCKED"
      ? "critical"
      : normalized === "PREVIEW" || normalized === "APPROVED" || normalized === "APPLYING" || normalized === "CHECKED"
        ? "warning"
        : "neutral";
  return <span className={`product-state-badge product-state-badge--${tone}`}>{normalized}</span>;
}

function ErrorState({ message }: { message: string }) {
  return <div className="product-state-panel product-state-panel--error"><div><strong>Gate 8 action failed</strong><p>{message}</p></div></div>;
}

function LoadingState({ label }: { label: string }) {
  return <div className="product-state-panel"><span className="product-spinner" /> <strong>{label}</strong></div>;
}

function recordSide(operation: EmergencyDomainPlan["operations"][number]) {
  return operation.after ?? operation.desired ?? operation.before ?? operation.current ?? null;
}

export function EmergencyDomainDashboard() {
  const provider = useEndpoint<EmergencyStatus>("emergency/status/");
  const domains = useEndpoint<DomainsResponse>("namecom/domains/");
  const domainNames = useMemo(
    () => domains.data?.domains.map(domainNameOf).filter(Boolean) ?? [],
    [domains.data],
  );
  const [sourceDomain, setSourceDomain] = useState("");
  const [keyword, setKeyword] = useState("domaintwin-rescue");
  const [searchResults, setSearchResults] = useState<EmergencySearchResult[]>([]);
  const [selectedCandidate, setSelectedCandidate] = useState<EmergencySearchResult | null>(null);
  const [checkedCandidate, setCheckedCandidate] = useState<EmergencySearchResult | null>(null);
  const [selectedPlanId, setSelectedPlanId] = useState<number | null>(null);
  const [localPlan, setLocalPlan] = useState<EmergencyDomainPlan | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  useEffect(() => {
    if (!sourceDomain && domainNames.length) setSourceDomain(domainNames[0]);
  }, [sourceDomain, domainNames]);

  const plans = useEndpoint<{ plans: EmergencyDomainPlan[]; totalCount: number }>(
    sourceDomain ? `emergency/domains/${encodeDomain(sourceDomain)}/plans/` : null,
  );
  const planSummaries = plans.data?.plans ?? [];

  useEffect(() => {
    if (!planSummaries.length) {
      setSelectedPlanId(null);
      return;
    }
    if (!selectedPlanId || !planSummaries.some((plan) => plan.id === selectedPlanId)) {
      setSelectedPlanId(planSummaries[0].id);
    }
  }, [planSummaries, selectedPlanId]);

  const detail = useEndpoint<{ plan: EmergencyDomainPlan }>(
    selectedPlanId ? `emergency/plans/${selectedPlanId}/` : null,
  );
  const activePlan = localPlan?.id === selectedPlanId ? localPlan : detail.data?.plan ?? null;
  const environment = String(provider.data?.environment ?? domains.data?.environment ?? "UNKNOWN").toUpperCase();

  function acceptPlan(plan: EmergencyDomainPlan) {
    setLocalPlan(plan);
    setSelectedPlanId(plan.id);
    plans.reload();
  }

  async function search() {
    setBusy("search");
    setActionError(null);
    setCheckedCandidate(null);
    try {
      const response = await api<EmergencySearchResponse>("emergency/search/", {
        method: "POST",
        body: JSON.stringify({ keyword, tldFilter: ["com", "net", "org"] }),
      });
      setSearchResults(response.results);
      const preferred = response.results.find((item) => item.gate8Supported) ?? response.results[0] ?? null;
      setSelectedCandidate(preferred);
    } catch (reason) {
      setActionError(reason instanceof Error ? reason.message : "Search failed");
    } finally {
      setBusy(null);
    }
  }

  async function check() {
    if (!selectedCandidate) return;
    setBusy("check");
    setActionError(null);
    try {
      const response = await api<{ result: EmergencySearchResult }>("emergency/check/", {
        method: "POST",
        body: JSON.stringify({ domainName: selectedCandidate.domainName }),
      });
      setCheckedCandidate(response.result);
    } catch (reason) {
      setActionError(reason instanceof Error ? reason.message : "Availability check failed");
    } finally {
      setBusy(null);
    }
  }

  async function createPreview() {
    const target = checkedCandidate?.domainName ?? selectedCandidate?.domainName;
    if (!sourceDomain || !target) return;
    setBusy("preview");
    setActionError(null);
    try {
      const response = await api<{ plan: EmergencyDomainPlan }>(
        `emergency/domains/${encodeDomain(sourceDomain)}/plans/`,
        { method: "POST", body: JSON.stringify({ targetDomain: target }) },
      );
      acceptPlan(response.plan);
    } catch (reason) {
      setActionError(reason instanceof Error ? reason.message : "Emergency preview failed");
    } finally {
      setBusy(null);
    }
  }

  async function approve() {
    if (!activePlan) return;
    setBusy("approve");
    setActionError(null);
    try {
      const response = await api<{ plan: EmergencyDomainPlan }>(`emergency/plans/${activePlan.id}/approve/`, {
        method: "POST",
        body: JSON.stringify({ approve: true }),
      });
      acceptPlan(response.plan);
    } catch (reason) {
      setActionError(reason instanceof Error ? reason.message : "Approval failed");
    } finally {
      setBusy(null);
    }
  }

  async function apply() {
    if (!activePlan) return;
    setBusy("apply");
    setActionError(null);
    try {
      const response = await api<{ plan: EmergencyDomainPlan }>(`emergency/plans/${activePlan.id}/apply/`, {
        method: "POST",
        body: JSON.stringify({ execute: true, targetDomain: activePlan.targetDomain }),
      });
      acceptPlan(response.plan);
      domains.reload();
    } catch (reason) {
      setActionError(reason instanceof Error ? reason.message : "Register + clone + verify failed");
      detail.reload();
      plans.reload();
    } finally {
      setBusy(null);
    }
  }

  const exactCandidateReady = Boolean(
    checkedCandidate?.gate8Supported && checkedCandidate.domainName === selectedCandidate?.domainName,
  );
  const verificationMatched = activePlan?.verification?.matched === true;

  return (
    <>
      <div className="product-page-heading">
        <div>
          <span className="eyebrow">GATE 8 · EMERGENCY DOMAIN</span>
          <h1>Emergency domain continuity</h1>
          <p>Search → check → preview → human approval → sandbox registration → clone known-good DNS → fingerprint verification.</p>
        </div>
        <div className="product-heading-actions">
          <span className={environment === "SANDBOX" ? "product-env product-env--sandbox product-env--large" : "product-env product-env--production product-env--large"}>{environment}</span>
          <StateBadge state={provider.data?.registrationEnabled ? "REGISTRATION ARMED" : "REGISTRATION BLOCKED"} />
        </div>
      </div>

      <div className="product-recovery-safety">
        <strong>Sandbox-only purchase boundary</strong>
        <span>Search and availability are read-only. Registration needs explicit plan approval, DNS mutation permission, a second registration flag, an exact target-domain execution confirmation, and can never run in production.</span>
      </div>

      {actionError ? <ErrorState message={actionError} /> : null}
      {provider.error ? <ErrorState message={provider.error} /> : null}

      <div className="product-metric-grid">
        <div className="product-metric"><span>1 · SEARCH</span><strong>{searchResults.length ? `${searchResults.length} RESULT(S)` : "READY"}</strong><small>name.com registration inventory</small></div>
        <div className="product-metric"><span>2 · CHECK</span><strong>{checkedCandidate ? (checkedCandidate.gate8Supported ? "AVAILABLE" : "BLOCKED") : "PENDING"}</strong><small>Exact pre-registration check</small></div>
        <div className="product-metric"><span>3 · REGISTER + CLONE</span><strong>{activePlan?.status ?? "NO PLAN"}</strong><small>Human-approved sandbox mutation</small></div>
        <div className="product-metric"><span>4 · VERIFY</span><strong>{verificationMatched ? "MATCH YES" : activePlan?.verifiedAt ? "MATCH NO" : "PENDING"}</strong><small>Known-good fingerprint proof</small></div>
      </div>

      <div className="product-grid product-grid--2 product-grid--lower">
        <article className="product-card">
          <div className="product-card-head">
            <div><span className="product-card-kicker">SOURCE TWIN</span><h3>Choose the protected domain</h3></div>
            <span className="product-provider-tag">KNOWN-GOOD DNS</span>
          </div>
          {domains.loading ? <p>Loading name.com domains…</p> : domains.error ? <p>{domains.error}</p> : (
            <label>
              <span>Source domain</span>
              <select value={sourceDomain} onChange={(event) => { setSourceDomain(event.target.value); setSelectedPlanId(null); setLocalPlan(null); }}>
                {domainNames.map((name) => <option value={name} key={name}>{name}</option>)}
              </select>
            </label>
          )}
          {sourceDomain ? <p className="product-muted">The emergency target will clone the trusted snapshot of <code>{sourceDomain}</code>. <Link className="product-text-link" href={`/app/domains/${encodeDomain(sourceDomain)}/snapshots`}>Inspect snapshots →</Link></p> : null}
        </article>

        <article className="product-card">
          <div className="product-card-head">
            <div><span className="product-card-kicker">SEARCH</span><h3>Find a standard rescue domain</h3></div>
            <span className="product-provider-tag">.COM · .NET · .ORG</span>
          </div>
          <label>
            <span>Keyword</span>
            <input value={keyword} onChange={(event) => setKeyword(event.target.value)} placeholder="domaintwin-rescue" />
          </label>
          <div className="product-inline-actions">
            <button className="button button--primary" type="button" disabled={busy === "search"} onClick={search}>{busy === "search" ? "Searching…" : "Search name.com"}</button>
          </div>
          <p className="product-muted">Discovery is restricted to <code>purchaseType=registration</code>. Premium domains can be shown but Gate 8 intentionally refuses to register them.</p>
        </article>
      </div>

      {searchResults.length ? (
        <article className="product-card product-grid--lower">
          <div className="product-card-head"><div><span className="product-card-kicker">SEARCH RESULTS</span><h3>Real provider availability + pricing</h3></div><span className="product-provider-tag">name.com</span></div>
          <div className="product-table-wrap">
            <table className="product-table">
              <thead><tr><th>Domain</th><th>Status</th><th>Purchase</th><th>Renewal</th><th>Class</th><th>Action</th></tr></thead>
              <tbody>
                {searchResults.map((result) => (
                  <tr key={result.domainName}>
                    <td><code>{result.domainName}</code></td>
                    <td><StateBadge state={result.gate8Supported ? "AVAILABLE" : "BLOCKED"} /></td>
                    <td>{result.purchasePrice !== null && result.purchasePrice !== undefined ? `$${result.purchasePrice}` : "—"}</td>
                    <td>{result.renewalPrice !== null && result.renewalPrice !== undefined ? `$${result.renewalPrice}` : "—"}</td>
                    <td>{result.premium ? "PREMIUM" : result.purchaseType.toUpperCase()}</td>
                    <td><button className="button button--secondary" type="button" disabled={!result.gate8Supported} onClick={() => { setSelectedCandidate(result); setCheckedCandidate(null); }}>Select</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </article>
      ) : null}

      {selectedCandidate ? (
        <div className="product-grid product-grid--2 product-grid--lower">
          <article className="product-card">
            <span className="product-card-kicker">CHECK</span>
            <h3>{selectedCandidate.domainName}</h3>
            <p>Search results can become stale. Gate 8 performs a second exact availability check immediately before a preview can exist.</p>
            <div className="product-inline-actions">
              <button className="button button--primary" type="button" disabled={busy === "check"} onClick={check}>{busy === "check" ? "Checking…" : "Check exact availability"}</button>
              {checkedCandidate ? <StateBadge state={checkedCandidate.gate8Supported ? "CHECKED" : "BLOCKED"} /> : null}
            </div>
          </article>
          <article className="product-card">
            <span className="product-card-kicker">PREVIEW</span>
            <h3>Registration + DNS clone plan</h3>
            <p>Creating the plan is read-only. It freezes the exact target, known-good snapshot, expected fingerprint and records that would be cloned.</p>
            <div className="product-inline-actions">
              <button className="button button--primary" type="button" disabled={!exactCandidateReady || busy === "preview"} onClick={createPreview}>{busy === "preview" ? "Planning…" : "Create emergency preview"}</button>
            </div>
          </article>
        </div>
      ) : null}

      {planSummaries.length ? (
        <article className="product-card product-grid--lower">
          <div className="product-card-head">
            <div><span className="product-card-kicker">PLAN HISTORY</span><h3>Emergency domain audit history</h3></div>
            <select value={selectedPlanId ?? ""} onChange={(event) => { setSelectedPlanId(Number(event.target.value)); setLocalPlan(null); }}>
              {planSummaries.map((plan) => <option key={plan.id} value={plan.id}>#{plan.id} · {plan.targetDomain} · {plan.status}</option>)}
            </select>
          </div>
        </article>
      ) : null}

      {detail.loading && selectedPlanId && !localPlan ? <LoadingState label="Loading emergency plan detail…" /> : null}
      {detail.error ? <ErrorState message={detail.error} /> : null}

      {activePlan ? (
        <>
          <section className={`product-recovery-status product-recovery-status--${activePlan.status.toLowerCase()}`}>
            <div>
              <span className="product-card-kicker">EMERGENCY PLAN #{activePlan.id}</span>
              <h2>{activePlan.targetDomain}</h2>
              <p>{activePlan.status} · source {activePlan.sourceDomain} · trusted snapshot v{activePlan.baselineVersion}</p>
            </div>
            <div><StateBadge state={activePlan.status} /><code>{compactFingerprint(activePlan.planFingerprint)}</code></div>
          </section>

          <div className="product-grid product-grid--2 product-grid--lower">
            <article className="product-card">
              <span className="product-card-kicker">HUMAN APPROVAL BOUNDARY</span>
              <h3>Register exactly {activePlan.targetDomain}</h3>
              <p>Provider result: {activePlan.availability.premium ? "premium" : "standard"} {activePlan.availability.purchaseType}. Purchase price shown by name.com: <strong>{activePlan.availability.purchasePrice !== null && activePlan.availability.purchasePrice !== undefined ? `$${activePlan.availability.purchasePrice}` : "—"}</strong>.</p>
              <div className="product-inline-actions">
                {activePlan.requiresApproval ? <button className="button button--primary" type="button" disabled={busy === "approve"} onClick={approve}>{busy === "approve" ? "Approving…" : "Approve emergency registration"}</button> : null}
                {activePlan.canApply ? <button className="button button--danger" type="button" disabled={!provider.data?.registrationEnabled || busy === "apply"} onClick={apply}>{busy === "apply" ? "Registering + cloning + verifying…" : "Register + clone + verify"}</button> : null}
                {activePlan.canApply && !provider.data?.registrationEnabled ? <StateBadge state="BLOCKED" /> : null}
              </div>
              {activePlan.canApply && !provider.data?.registrationEnabled ? <p className="product-muted">Apply is blocked until the backend is explicitly armed for the sandbox drill. Search, check and preview stay usable.</p> : null}
            </article>

            <article className="product-card">
              <span className="product-card-kicker">REGISTRATION RESULT</span>
              <h3>{activePlan.registration.domainName ?? "Not registered yet"}</h3>
              <dl className="product-domain-meta">
                <div><dt>Order</dt><dd>{activePlan.registration.order ?? "—"}</dd></div>
                <div><dt>Total paid</dt><dd>{activePlan.registration.totalPaid !== null && activePlan.registration.totalPaid !== undefined ? `$${activePlan.registration.totalPaid}` : "—"}</dd></div>
                <div><dt>Created</dt><dd>{formatDate(activePlan.registration.createDate)}</dd></div>
                <div><dt>Expires</dt><dd>{formatDate(activePlan.registration.expireDate)}</dd></div>
              </dl>
              <p className="product-muted">Contacts are never rendered or persisted by the Gate 8 response boundary.</p>
            </article>
          </div>

          <article className="product-card product-grid--lower">
            <div className="product-card-head"><div><span className="product-card-kicker">CLONE PREVIEW</span><h3>Known-good DNS operations</h3></div><span className="product-provider-tag">{activePlan.operationCount} OPS</span></div>
            {activePlan.operations.length ? (
              <div className="product-table-wrap">
                <table className="product-table"><thead><tr><th>Action</th><th>Record</th><th>Answer</th><th>TTL</th></tr></thead><tbody>
                  {activePlan.operations.map((operation, index) => {
                    const record = recordSide(operation);
                    return <tr key={`${operation.action}-${index}`}><td><StateBadge state={operation.action} /></td><td><code>{record?.type ?? "—"} {record?.host || "@"}</code></td><td><code>{record?.answer ?? "—"}</code></td><td>{record?.ttl ?? "—"}</td></tr>;
                  })}
                </tbody></table>
              </div>
            ) : <p>No DNS records are required by the trusted snapshot.</p>}
          </article>

          <div className="product-grid product-grid--2 product-grid--lower">
            <article className="product-card">
              <span className="product-card-kicker">VERIFY</span>
              <h3>Emergency twin fingerprint</h3>
              <div className="product-verification-grid">
                <div><span>EXPECTED</span><code>{compactFingerprint(activePlan.expectedFingerprint)}</code></div>
                <div><span>ACTUAL</span><code>{compactFingerprint(activePlan.actualFingerprint)}</code></div>
                <div><span>MATCH</span><strong>{verificationMatched ? "YES" : activePlan.verifiedAt ? "NO" : "PENDING"}</strong></div>
              </div>
            </article>
            <article className="product-card">
              <span className="product-card-kicker">FINAL STATE</span>
              <h3>{activePlan.status === "READY" ? "Emergency domain ready" : "Continuity workflow in progress"}</h3>
              <p>{activePlan.status === "READY" ? `${activePlan.targetDomain} is registered in name.com sandbox and its live DNS fingerprint exactly matches trusted snapshot v${activePlan.baselineVersion}.` : "READY is rendered only after a fresh provider read proves that expected and actual DNS fingerprints match."}</p>
              <StateBadge state={activePlan.status} />
            </article>
          </div>

          <article className="product-card product-grid--lower">
            <div className="product-card-head"><div><span className="product-card-kicker">AUDIT TRAIL</span><h3>Search-to-ready evidence boundary</h3></div><span className="product-provider-tag">{activePlan.audit?.length ?? 0} EVENTS</span></div>
            {activePlan.audit?.length ? <ol className="product-timeline">{activePlan.audit.map((event) => <li key={event.sequence}><span>{event.sequence}</span><div><strong>{event.eventType.replaceAll("_", " ")}</strong><small>{formatDate(event.occurredAt)}</small></div></li>)}</ol> : <p>No audit events loaded.</p>}
          </article>
        </>
      ) : null}
    </>
  );
}
