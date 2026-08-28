"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  api,
  compactFingerprint,
  DomainsResponse,
  domainNameOf,
  encodeDomain,
  formatDate,
  MonitorStatus,
  NameComStatus,
  RecoveryOperation,
  RecoveryPlan,
  DnsRecord,
} from "@/lib/domaintwin";

type LoadState<T> = {
  data: T | null;
  error: string | null;
  loading: boolean;
  reload: () => void;
};

type RecoveryDashboardProps = {
  initialDomain?: string;
  initialIncidentId?: number | null;
};

const RECOVERY_STEPS = ["DETECTED", "PREVIEW", "APPROVED", "APPLY", "VERIFIED"] as const;

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
      .then((payload) => {
        if (!cancelled) setData(payload);
      })
      .catch((reason) => {
        if (!cancelled) {
          setError(reason instanceof Error ? reason.message : "Request failed");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [path, version]);

  return {
    data,
    error,
    loading,
    reload: () => setVersion((value) => value + 1),
  };
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

function LoadingState({ label }: { label: string }) {
  return (
    <div className="product-state-panel">
      <span className="product-spinner" /> <strong>{label}</strong>
    </div>
  );
}

function ErrorState({ message }: { message: string }) {
  return (
    <div className="product-state-panel product-state-panel--error">
      <div><strong>External call failed</strong><p>{message}</p></div>
    </div>
  );
}

function EmptyState({ title, copy }: { title: string; copy: string }) {
  return <div className="product-empty"><strong>{title}</strong><p>{copy}</p></div>;
}

function operationSide(operation: RecoveryOperation, side: "before" | "after"): DnsRecord | null {
  if (side === "before") return operation.before ?? operation.current ?? null;
  return operation.after ?? operation.desired ?? null;
}

function RecoveryOperations({ plan }: { plan: RecoveryPlan }) {
  if (!plan.operations.length) {
    return <EmptyState title="No mutation required" copy="Current DNS already matches the known-good target. DomainTwin only needs to verify the live fingerprint." />;
  }

  return (
    <div className="product-table-wrap">
      <table className="product-table">
        <thead>
          <tr><th>Action</th><th>Record</th><th>Current</th><th>Restore</th></tr>
        </thead>
        <tbody>
          {plan.operations.map((operation, index) => {
            const before = operationSide(operation, "before");
            const after = operationSide(operation, "after");
            const record = after ?? before;
            return (
              <tr key={`${operation.action}-${index}`}>
                <td><StateBadge state={operation.action} /></td>
                <td><code>{record?.type ?? "—"} {record?.host || "@"}</code></td>
                <td><code>{before?.answer ?? "—"}</code></td>
                <td><code>{after?.answer ?? "—"}</code></td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function recoveryStepIndex(plan: RecoveryPlan | null, incidentId: number | null): number {
  if (!plan) return incidentId ? 0 : -1;
  const status = String(plan.status).toUpperCase();
  if (status === "PREVIEW") return 1;
  if (status === "APPROVED") return 2;
  if (status === "APPLYING" || status === "PARTIAL" || status === "FAILED" || status === "STALE") return 3;
  if (status === "RECOVERED") return 4;
  return 1;
}

export function RecoveryDashboard({ initialDomain = "", initialIncidentId = null }: RecoveryDashboardProps) {
  const provider = useEndpoint<NameComStatus>("namecom/status/");
  const domains = useEndpoint<DomainsResponse>("namecom/domains/");
  const names = useMemo(
    () => domains.data?.domains.map(domainNameOf).filter(Boolean) ?? [],
    [domains.data],
  );

  const [selectedDomain, setSelectedDomain] = useState("");
  const [selectedPlanId, setSelectedPlanId] = useState<number | null>(null);
  const [plans, setPlans] = useState<RecoveryPlan[]>([]);
  const [plansLoaded, setPlansLoaded] = useState(false);
  const [plansError, setPlansError] = useState<string | null>(null);
  const [activePlan, setActivePlan] = useState<RecoveryPlan | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [confirmMutation, setConfirmMutation] = useState(false);

  useEffect(() => {
    if (!selectedDomain && names.length) {
      setSelectedDomain(initialDomain && names.includes(initialDomain) ? initialDomain : names[0]);
    }
  }, [initialDomain, names, selectedDomain]);

  const monitor = useEndpoint<MonitorStatus>(
    selectedDomain ? `monitor/domains/${encodeDomain(selectedDomain)}/status/` : null,
  );

  useEffect(() => {
    if (!names.length) {
      if (domains.data) setPlansLoaded(true);
      return;
    }

    let cancelled = false;
    setPlansLoaded(false);
    setPlansError(null);

    Promise.all(
      names.map((name) => api<{ plans: RecoveryPlan[] }>(`recovery/domains/${encodeDomain(name)}/plans/`)),
    )
      .then((responses) => {
        if (cancelled) return;
        setPlans(
          responses
            .flatMap((response) => response.plans)
            .sort((a, b) => +new Date(b.createdAt) - +new Date(a.createdAt)),
        );
      })
      .catch((reason) => {
        if (!cancelled) setPlansError(reason instanceof Error ? reason.message : "Recovery plans failed");
      })
      .finally(() => {
        if (!cancelled) setPlansLoaded(true);
      });

    return () => {
      cancelled = true;
    };
  }, [names, domains.data]);

  const domainPlans = useMemo(
    () => plans.filter((plan) => plan.domainName === selectedDomain),
    [plans, selectedDomain],
  );

  useEffect(() => {
    if (!domainPlans.length) {
      setSelectedPlanId(null);
      return;
    }
    if (!selectedPlanId || !domainPlans.some((plan) => plan.id === selectedPlanId)) {
      setSelectedPlanId(domainPlans[0].id);
    }
  }, [domainPlans, selectedPlanId]);

  const activeSummary = useMemo(
    () => domainPlans.find((plan) => plan.id === selectedPlanId) ?? domainPlans[0] ?? null,
    [domainPlans, selectedPlanId],
  );

  useEffect(() => {
    setConfirmMutation(false);
    if (!activeSummary) {
      setActivePlan(null);
      setDetailError(null);
      setDetailLoading(false);
      return;
    }

    let cancelled = false;
    setDetailLoading(true);
    setDetailError(null);

    api<{ plan: RecoveryPlan }>(`recovery/plans/${activeSummary.id}/`)
      .then((response) => {
        if (!cancelled) setActivePlan(response.plan);
      })
      .catch((reason) => {
        if (!cancelled) {
          setActivePlan(activeSummary);
          setDetailError(reason instanceof Error ? reason.message : "Recovery detail failed");
        }
      })
      .finally(() => {
        if (!cancelled) setDetailLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [activeSummary]);

  function upsert(plan: RecoveryPlan) {
    setPlans((current) => [plan, ...current.filter((item) => item.id !== plan.id)]);
    setSelectedPlanId(plan.id);
    setActivePlan(plan);
    setConfirmMutation(false);
  }

  async function createPreview() {
    if (!selectedDomain) return;
    setBusy("preview");
    setActionError(null);
    try {
      const response = await api<{ plan: RecoveryPlan }>(
        `recovery/domains/${encodeDomain(selectedDomain)}/plans/`,
        { method: "POST" },
      );
      upsert(response.plan);
    } catch (reason) {
      setActionError(reason instanceof Error ? reason.message : "Preview failed");
    } finally {
      setBusy(null);
    }
  }

  async function approve() {
    if (!activePlan) return;
    setBusy("approve");
    setActionError(null);
    try {
      const response = await api<{ plan: RecoveryPlan }>(`recovery/plans/${activePlan.id}/approve/`, {
        method: "POST",
        body: JSON.stringify({ approve: true }),
      });
      upsert(response.plan);
    } catch (reason) {
      setActionError(reason instanceof Error ? reason.message : "Approval failed");
    } finally {
      setBusy(null);
    }
  }

  async function apply() {
    if (!activePlan) return;
    const verificationOnly = activePlan.operationCount === 0;
    if (!verificationOnly && !confirmMutation) {
      setActionError("Confirm the DNS mutation boundary before applying this recovery plan.");
      return;
    }
    setBusy("apply");
    setActionError(null);
    try {
      const response = await api<{ plan: RecoveryPlan }>(`recovery/plans/${activePlan.id}/apply/`, {
        method: "POST",
      });
      upsert(response.plan);
      monitor.reload();
    } catch (reason) {
      setActionError(reason instanceof Error ? reason.message : "Recovery apply failed");
    } finally {
      setBusy(null);
    }
  }

  const environment = (provider.data?.environment ?? domains.data?.environment ?? "UNKNOWN").toUpperCase();
  const verified = activePlan?.verification as {
    matched?: boolean;
    expectedFingerprint?: string;
    actualFingerprint?: string;
  } | undefined;
  const verificationOnly = Boolean(activePlan && activePlan.operationCount === 0);
  const contextIncidentId = monitor.data?.activeIncident?.id ?? initialIncidentId ?? activePlan?.incidentId ?? null;
  const stepIndex = recoveryStepIndex(activePlan, contextIncidentId);
  const problemState = Boolean(activePlan && ["PARTIAL", "FAILED", "STALE"].includes(String(activePlan.status).toUpperCase()));

  return (
    <>
      <div className="product-page-heading">
        <div>
          <span className="eyebrow">RECOVERY CONTROL</span>
          <h1>Verified recovery workspace</h1>
          <p>Preview exact Current → Known-Good operations, require explicit approval, mutate through name.com only when needed, and independently verify the resulting fingerprint.</p>
        </div>
        <div className="product-heading-actions">
          <span className={environment === "PRODUCTION" ? "product-env product-env--production product-env--large" : "product-env product-env--sandbox product-env--large"}>{environment}</span>
        </div>
      </div>

      {contextIncidentId && selectedDomain ? (
        <div className="p6-recovery-context">
          <div>
            <strong>Recovery target · {selectedDomain} · incident #{contextIncidentId}</strong>
            <p>{monitor.data?.activeIncident ? `${monitor.data.activeIncident.severity} risk ${monitor.data.activeIncident.score}/100 · detected by automatic monitoring` : "Opened from incident context; recovery remains approval-gated."}</p>
          </div>
          <Link href={`/app/incidents/${contextIncidentId}`}>Inspect deterministic evidence →</Link>
        </div>
      ) : null}

      <div className="p6-recovery-steps" aria-label="Recovery progress">
        {RECOVERY_STEPS.map((step, index) => {
          const complete = stepIndex > index || (stepIndex === 4 && index === 4);
          const current = stepIndex === index && !complete;
          const problem = problemState && index === 3;
          return (
            <div className={`p6-recovery-step${complete ? " is-complete" : ""}${current ? " is-current" : ""}${problem ? " is-problem" : ""}`} key={step}>
              <span>0{index + 1}</span>
              <strong>{step}</strong>
            </div>
          );
        })}
      </div>

      <div className="product-recovery-safety">
        <strong>Human approval boundary</strong>
        <span>Preview never mutates DNS. If the target already matches live DNS, DomainTwin performs verification only; provider mutations remain guarded by the backend.</span>
      </div>

      {actionError ? <ErrorState message={actionError} /> : null}
      {plansError ? <ErrorState message={plansError} /> : null}

      {(domains.loading || !plansLoaded) ? (
        <LoadingState label="Loading recovery state…" />
      ) : domains.error ? (
        <ErrorState message={domains.error} />
      ) : !names.length ? (
        <EmptyState title="No domains available" copy="Recovery needs a connected name.com domain and a known-good snapshot." />
      ) : (
        <>
          <div className="product-recovery-toolbar">
            <label>
              <span>DOMAIN</span>
              <select value={selectedDomain} onChange={(event) => { setSelectedDomain(event.target.value); setSelectedPlanId(null); setConfirmMutation(false); }}>
                {names.map((name) => <option key={name} value={name}>{name}</option>)}
              </select>
            </label>
            {domainPlans.length ? (
              <label>
                <span>PLAN HISTORY</span>
                <select value={selectedPlanId ?? ""} onChange={(event) => setSelectedPlanId(Number(event.target.value))}>
                  {domainPlans.map((plan) => (
                    <option key={plan.id} value={plan.id}>#{plan.id} · {plan.status} · {plan.operationCount} ops</option>
                  ))}
                </select>
              </label>
            ) : null}
            <button className="button button--secondary" disabled={busy === "preview"} onClick={createPreview} type="button">
              {busy === "preview" ? "Planning…" : activePlan ? "Re-check / create preview" : "Create rollback preview"}
            </button>
            {activePlan?.requiresApproval ? (
              <button className="button button--primary" disabled={busy === "approve"} onClick={approve} type="button">
                {busy === "approve" ? "Approving…" : verificationOnly ? "Approve verification" : "Approve recovery"}
              </button>
            ) : null}
            {activePlan?.canApply ? (
              <button
                className={verificationOnly ? "button button--primary" : "button button--danger"}
                disabled={busy === "apply" || (!verificationOnly && !confirmMutation)}
                onClick={apply}
                type="button"
              >
                {busy === "apply" ? (verificationOnly ? "Verifying current DNS…" : "Applying + verifying…") : verificationOnly ? "Verify current DNS" : "Apply approved recovery"}
              </button>
            ) : null}
          </div>

          {activePlan?.canApply && !verificationOnly ? (
            <label className="p6-recovery-confirm">
              <input type="checkbox" checked={confirmMutation} onChange={(event) => setConfirmMutation(event.target.checked)} />
              <span><strong>Mutation confirmation:</strong> I reviewed the exact operations above and understand that Apply will change live DNS through the approved provider boundary.</span>
            </label>
          ) : null}

          {detailLoading ? <LoadingState label="Loading full recovery audit…" /> : null}
          {detailError ? <ErrorState message={`Plan summary loaded, but detailed audit could not be read: ${detailError}`} /> : null}

          {!activePlan ? (
            <EmptyState title="No recovery plan for this domain" copy="Create a rollback preview. DomainTwin will read live name.com DNS and compare it with the known-good snapshot without mutating anything." />
          ) : (
            <>
              <section className={`product-recovery-status product-recovery-status--${activePlan.status.toLowerCase()}`}>
                <div>
                  <span className="product-card-kicker">PLAN #{activePlan.id}</span>
                  <h2>{activePlan.status}</h2>
                  <p>{activePlan.operationCount} operation(s) · target snapshot v{activePlan.baselineVersion}{verificationOnly ? " · verification-only path" : ""}</p>
                </div>
                <div><StateBadge state={activePlan.status} /><code>{compactFingerprint(activePlan.planFingerprint)}</code></div>
              </section>

              <article className="product-card product-grid--lower">
                <div className="product-card-head">
                  <div><span className="product-card-kicker">ROLLBACK PREVIEW</span><h3>Exact name.com operations</h3></div>
                  <span className="product-provider-tag">{activePlan.operationCount} OPS</span>
                </div>
                <RecoveryOperations plan={activePlan} />
              </article>

              <div className="product-grid product-grid--2 product-grid--lower">
                <article className="product-card">
                  <span className="product-card-kicker">VERIFICATION</span>
                  <h3>{activePlan.status === "RECOVERED" ? "Expected equals actual" : verificationOnly ? "Verify already-matching DNS" : "Post-mutation proof"}</h3>
                  <div className="product-verification-grid">
                    <div><span>EXPECTED</span><code>{compactFingerprint(activePlan.targetFingerprint)}</code></div>
                    <div><span>ACTUAL</span><code>{compactFingerprint(verified?.actualFingerprint)}</code></div>
                    <div><span>MATCH</span><strong>{verified?.matched === true ? "YES" : verified?.matched === false ? "NO" : "PENDING"}</strong></div>
                  </div>
                </article>

                <article className="product-card">
                  <span className="product-card-kicker">AUDIT TRAIL</span>
                  <h3>Recovery events</h3>
                  {!activePlan.audit?.length ? (
                    <p>No detailed recovery events are stored for this plan.</p>
                  ) : (
                    <div className="product-mini-timeline">
                      {activePlan.audit.map((event) => (
                        <div key={`${event.sequence}-${event.eventType}`}>
                          <span>{event.sequence}</span>
                          <strong>{event.eventType.replaceAll("_", " ")}</strong>
                          <small>{formatDate(event.occurredAt)}</small>
                        </div>
                      ))}
                    </div>
                  )}
                </article>
              </div>

              {activePlan.incidentId ? (
                <div className="product-follow-link">
                  <span>Linked incident #{activePlan.incidentId}</span>
                  <Link href={`/app/incidents/${activePlan.incidentId}`}>Inspect evidence →</Link>
                </div>
              ) : null}
            </>
          )}
        </>
      )}
    </>
  );
}
