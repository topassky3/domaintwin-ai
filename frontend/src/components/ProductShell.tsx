"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ReactNode, useEffect, useMemo, useState } from "react";
import { api, DomainsResponse, domainNameOf, NameComStatus } from "@/lib/domaintwin";

const nav = [
  ["OV", "Overview", "/app/overview"],
  ["DM", "Domains", "/app/domains"],
  ["IN", "Incidents", "/app/incidents"],
  ["RC", "Recovery", "/app/recovery"],
] as const;

export function ProductShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const [provider, setProvider] = useState<NameComStatus | null>(null);
  const [providerError, setProviderError] = useState<string | null>(null);
  const [domains, setDomains] = useState<string[]>([]);

  useEffect(() => {
    let cancelled = false;
    Promise.allSettled([
      api<NameComStatus>("namecom/status/"),
      api<DomainsResponse>("namecom/domains/"),
    ]).then(([statusResult, domainsResult]) => {
      if (cancelled) return;
      if (statusResult.status === "fulfilled") {
        setProvider(statusResult.value);
        setProviderError(null);
      } else {
        setProviderError(statusResult.reason instanceof Error ? statusResult.reason.message : "Provider unavailable");
      }
      if (domainsResult.status === "fulfilled") {
        setDomains(domainsResult.value.domains.map(domainNameOf).filter(Boolean));
      }
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const activeDomain = useMemo(() => {
    const match = pathname.match(/^\/app\/domains\/([^/]+)/);
    if (match) return decodeURIComponent(match[1]);
    return domains[0] ?? null;
  }, [pathname, domains]);

  const environment = provider?.environment?.toUpperCase() ?? "UNKNOWN";
  const environmentClass = environment === "PRODUCTION" ? "product-env--production" : "product-env--sandbox";

  return (
    <div className="product-root">
      <aside className="product-sidebar">
        <Link className="product-brand" href="/app/overview">
          <span className="brand-mark">D</span>
          <span><strong>DomainTwin</strong><small>CONTROL PLANE</small></span>
        </Link>

        <nav className="product-nav" aria-label="Product navigation">
          {nav.map(([icon, label, href]) => {
            const active = pathname === href || (href !== "/app/overview" && pathname.startsWith(href));
            return (
              <Link className={active ? "product-nav-link is-active" : "product-nav-link"} href={href} key={href}>
                <span>{icon}</span>{label}
              </Link>
            );
          })}
        </nav>

        <div className="product-sidebar-section">
          <span className="product-sidebar-label">ACTIVE DOMAIN</span>
          {activeDomain ? (
            <>
              <Link className="product-domain-shortcut" href={`/app/domains/${encodeURIComponent(activeDomain)}`}>
                <strong>{activeDomain}</strong>
                <small>Open workspace →</small>
              </Link>
              <div className="product-subnav">
                <Link href={`/app/domains/${encodeURIComponent(activeDomain)}/dns`}>DNS records</Link>
                <Link href={`/app/domains/${encodeURIComponent(activeDomain)}/snapshots`}>Snapshots</Link>
              </div>
            </>
          ) : (
            <p className="product-sidebar-empty">No domain loaded yet.</p>
          )}
        </div>

        <div className="product-sidebar-spacer" />
        <div className="product-provider-card">
          <div className="product-provider-row">
            <span className={`product-env ${environmentClass}`}>{environment}</span>
            <span className={provider ? "provider-dot is-online" : "provider-dot"} />
          </div>
          <strong>{provider?.provider ?? "name.com"}</strong>
          <small>{provider ? "API connected" : providerError ? "Provider unavailable" : "Checking provider…"}</small>
          <p>Credentials stay server-side. Browser requests pass through the DomainTwin proxy.</p>
        </div>
      </aside>

      <div className="product-stage">
        <header className="product-topbar">
          <div>
            <span className="product-topbar-label">DOMAIN CONTINUITY CONTROL PLANE</span>
            <strong>{activeDomain ?? "Domain portfolio"}</strong>
          </div>
          <div className="product-topbar-actions">
            <span className={`product-env product-env--large ${environmentClass}`}>{environment}</span>
            <span className={provider ? "product-connection is-online" : "product-connection"}>
              <i /> {provider ? "NAME.COM CONNECTED" : "PROVIDER OFFLINE"}
            </span>
            <Link className="button button--secondary" href="/demo">Public demo</Link>
          </div>
        </header>
        <main className="product-content">{children}</main>
      </div>
    </div>
  );
}
