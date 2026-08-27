"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { ReactNode, useEffect, useMemo, useState } from "react";
import type { AuthUser, OrganizationMembership } from "@/lib/auth";
import { listOrganizations, selectActiveOrganization, signOut } from "@/lib/auth";
import { api, DomainsResponse, domainNameOf, NameComStatus } from "@/lib/domaintwin";

const nav = [
  ["OV", "Overview", "/app/overview"],
  ["DM", "Domains", "/app/domains"],
  ["IN", "Incidents", "/app/incidents"],
  ["RC", "Recovery", "/app/recovery"],
  ["ED", "Emergency", "/app/emergency"],
] as const;

export function ProductShell({ children, user }: { children: ReactNode; user: AuthUser }) {
  const pathname = usePathname();
  const router = useRouter();
  const [provider, setProvider] = useState<NameComStatus | null>(null);
  const [providerError, setProviderError] = useState<string | null>(null);
  const [domains, setDomains] = useState<string[]>([]);
  const [domainsReachable, setDomainsReachable] = useState(false);
  const [fallbackEnvironment, setFallbackEnvironment] = useState<string | null>(null);
  const [signingOut, setSigningOut] = useState(false);
  const [organizations, setOrganizations] = useState<OrganizationMembership[]>([]);
  const [activeOrganization, setActiveOrganization] = useState<OrganizationMembership | null>(null);
  const [selectingOrganization, setSelectingOrganization] = useState(false);
  const [organizationError, setOrganizationError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    listOrganizations()
      .then((directory) => {
        if (cancelled) return;
        setOrganizations(directory.organizations);
        setActiveOrganization(directory.activeOrganization);
        setOrganizationError(null);
      })
      .catch((reason) => {
        if (cancelled) return;
        setOrganizationError(reason instanceof Error ? reason.message : "Organization context unavailable");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    let retryTimer: ReturnType<typeof setTimeout> | null = null;

    async function readStatus() {
      try {
        const value = await api<NameComStatus>("namecom/status/");
        if (cancelled) return;
        setProvider(value);
        setProviderError(null);
      } catch (reason) {
        if (cancelled) return;
        setProviderError(reason instanceof Error ? reason.message : "Provider status unavailable");
      }
    }

    Promise.allSettled([
      api<NameComStatus>("namecom/status/"),
      api<DomainsResponse>("namecom/domains/"),
    ]).then(([statusResult, domainsResult]) => {
      if (cancelled) return;

      if (statusResult.status === "fulfilled") {
        setProvider(statusResult.value);
        setProviderError(null);
      } else {
        setProviderError(statusResult.reason instanceof Error ? statusResult.reason.message : "Provider status unavailable");
        retryTimer = setTimeout(() => void readStatus(), 1200);
      }

      if (domainsResult.status === "fulfilled") {
        setDomains(domainsResult.value.domains.map(domainNameOf).filter(Boolean));
        setDomainsReachable(true);
        setFallbackEnvironment(domainsResult.value.environment ?? null);
      } else {
        setDomainsReachable(false);
      }
    });

    return () => {
      cancelled = true;
      if (retryTimer) clearTimeout(retryTimer);
    };
  }, []);

  const activeDomain = useMemo(() => {
    const match = pathname.match(/^\/app\/domains\/([^/]+)/);
    if (match) return decodeURIComponent(match[1]);
    return domains[0] ?? null;
  }, [pathname, domains]);

  const providerReachable = Boolean(provider) || domainsReachable;
  const environment = String(provider?.environment ?? fallbackEnvironment ?? "UNKNOWN").toUpperCase();
  const environmentClass = environment === "PRODUCTION"
    ? "product-env--production"
    : environment === "SANDBOX"
      ? "product-env--sandbox"
      : "";
  const connectionLabel = provider
    ? "NAME.COM CONNECTED"
    : domainsReachable
      ? "NAME.COM CONNECTED"
      : providerError
        ? "PROVIDER STATUS UNAVAILABLE"
        : "CHECKING PROVIDER";
  const providerDetail = provider
    ? "API connected"
    : domainsReachable
      ? "API connected · status fallback"
      : providerError
        ? "Provider status unavailable"
        : "Checking provider…";

  async function handleOrganizationChange(organizationId: string) {
    if (!organizationId || selectingOrganization) return;
    setSelectingOrganization(true);
    setOrganizationError(null);
    try {
      const selected = await selectActiveOrganization(organizationId);
      setActiveOrganization(selected);
      window.location.assign(pathname);
    } catch (reason) {
      setOrganizationError(reason instanceof Error ? reason.message : "Unable to switch organization");
      setSelectingOrganization(false);
    }
  }

  async function handleSignOut() {
    if (signingOut) return;
    setSigningOut(true);
    try {
      await signOut();
    } finally {
      router.replace("/login");
      router.refresh();
    }
  }

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
            <span className={providerReachable ? "provider-dot is-online" : "provider-dot"} />
          </div>
          <strong>{provider?.provider ?? "name.com"}</strong>
          <small>{providerDetail}</small>
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
            {organizations.length > 0 ? (
              <select
                aria-label="Active organization"
                value={activeOrganization?.organizationId ?? ""}
                disabled={selectingOrganization}
                onChange={(event) => void handleOrganizationChange(event.target.value)}
                title={organizationError ?? "Server-validated active organization"}
              >
                <option value="" disabled>Select organization</option>
                {organizations.map((organization) => (
                  <option value={organization.organizationId} key={organization.organizationId}>
                    {organization.organizationName} · {organization.role}
                  </option>
                ))}
              </select>
            ) : null}
            <span className={`product-env product-env--large ${environmentClass}`}>{environment}</span>
            <span className="product-connection is-online" title={`Capabilities: ${user.capabilities.join(", ")}`}>
              <i /> {user.role ?? "SELECT TENANT"} · {user.username}
            </span>
            <span className={providerReachable ? "product-connection is-online" : "product-connection"}>
              <i /> {connectionLabel}
            </span>
            <Link className="button button--secondary" href="/demo">Public demo</Link>
            <button className="button button--secondary" type="button" onClick={() => void handleSignOut()} disabled={signingOut}>
              {signingOut ? "Signing out…" : "Sign out"}
            </button>
          </div>
        </header>
        <main className="product-content">{children}</main>
      </div>
    </div>
  );
}
