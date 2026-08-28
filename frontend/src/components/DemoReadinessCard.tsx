"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/domaintwin";

type ReadinessCheck = {
  id: string;
  label: string;
  status: "PASS" | "FAIL" | "WARN" | string;
  required: boolean;
  detail: string;
};

type DemoReadiness = {
  status: "READY" | "BLOCKED" | string;
  organization: { id: string; name: string; slug: string };
  environment: string;
  primaryDomain: string | null;
  managedDomainCount: number;
  knownGoodDomainCount: number;
  blockerCount: number;
  warningCount: number;
  checks: ReadinessCheck[];
};

export function DemoReadinessCard() {
  const [data, setData] = useState<DemoReadiness | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await api<DemoReadiness>("demo/readiness/"));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Demo preflight unavailable");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (loading && !data) {
    return (
      <section className="p7-readiness p7-readiness--loading">
        <span className="product-spinner" />
        <div><span className="product-card-kicker">HACKATHON PREFLIGHT</span><strong>Checking demo readiness…</strong></div>
      </section>
    );
  }

  if (error && !data) {
    return (
      <section className="p7-readiness p7-readiness--blocked">
        <div><span className="product-card-kicker">HACKATHON PREFLIGHT</span><h2>Preflight unavailable</h2><p>{error}</p></div>
        <div className="p7-readiness-actions"><button className="button button--secondary" type="button" onClick={() => void load()}>Retry preflight</button><Link className="button button--secondary" href="/demo">Open safe demo</Link></div>
      </section>
    );
  }

  if (!data) return null;

  const ready = data.status === "READY";
  return (
    <section className={ready ? "p7-readiness p7-readiness--ready" : "p7-readiness p7-readiness--blocked"}>
      <div className="p7-readiness-head">
        <div>
          <span className="product-card-kicker">HACKATHON PREFLIGHT · {data.organization.slug}</span>
          <div className="p7-readiness-title"><h2>{ready ? "Demo ready" : "Demo blocked"}</h2><span>{data.status}</span></div>
          <p>{ready ? "Required checks pass. Warnings are non-blocking and can be reviewed before presenting." : `${data.blockerCount} required check(s) must be fixed before using the live recovery path.`}</p>
        </div>
        <div className="p7-readiness-summary"><strong>{data.blockerCount}</strong><span>BLOCKERS</span><strong>{data.warningCount}</strong><span>WARNINGS</span></div>
      </div>

      <div className="p7-readiness-checks">
        {data.checks.map((check) => (
          <div className={`p7-readiness-check p7-readiness-check--${check.status.toLowerCase()}`} key={check.id}>
            <span>{check.status}</span>
            <div><strong>{check.label}</strong><small>{check.detail}</small></div>
          </div>
        ))}
      </div>

      <div className="p7-readiness-footer">
        <span>{data.primaryDomain ? `Primary demo domain: ${data.primaryDomain}` : "No demo domain selected yet"} · {String(data.environment).toUpperCase()}</span>
        <div className="p7-readiness-actions"><button className="button button--secondary" type="button" disabled={loading} onClick={() => void load()}>{loading ? "Checking…" : "Re-run preflight"}</button><Link className="button button--primary" href="/demo">Open judge walkthrough</Link></div>
      </div>
    </section>
  );
}
