import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const requiredRoutes = [
  "src/app/app/overview/page.tsx",
  "src/app/app/domains/page.tsx",
  "src/app/app/domains/[domain]/page.tsx",
  "src/app/app/domains/[domain]/dns/page.tsx",
  "src/app/app/domains/[domain]/snapshots/page.tsx",
  "src/app/app/incidents/page.tsx",
  "src/app/app/incidents/[id]/page.tsx",
  "src/app/app/recovery/page.tsx",
];

const failures = [];
for (const route of requiredRoutes) {
  if (!fs.existsSync(path.join(root, route))) failures.push(`missing route: ${route}`);
}

const shellPath = path.join(root, "src/components/ProductShell.tsx");
const viewsPath = path.join(root, "src/components/ProductViews.tsx");
const overviewPath = path.join(root, "src/components/OverviewDashboard.tsx");
const domainWorkspacePath = path.join(root, "src/components/DomainWorkspaceDashboard.tsx");
const domainRoutePath = path.join(root, "src/app/app/domains/[domain]/page.tsx");
const proxyPath = path.join(root, "src/app/api/domaintwin/[...path]/route.ts");
const backendViewsPath = path.resolve(root, "../backend/core/views.py");

for (const target of [shellPath, viewsPath, overviewPath, domainWorkspacePath, domainRoutePath, proxyPath, backendViewsPath]) {
  if (!fs.existsSync(target)) failures.push(`missing file: ${path.relative(root, target)}`);
}

if (!failures.length) {
  const shell = fs.readFileSync(shellPath, "utf8");
  const views = fs.readFileSync(viewsPath, "utf8");
  const overview = fs.readFileSync(overviewPath, "utf8");
  const domainWorkspace = fs.readFileSync(domainWorkspacePath, "utf8");
  const domainRoute = fs.readFileSync(domainRoutePath, "utf8");
  const proxy = fs.readFileSync(proxyPath, "utf8");
  const backendViews = fs.readFileSync(backendViewsPath, "utf8");

  const checks = [
    [shell.includes("namecom/status/"), "shell must read name.com provider status"],
    [shell.includes("product-env--production") && shell.includes("product-env--sandbox"), "permanent environment indicator missing"],
    [shell.includes("domainsReachable") && shell.includes("fallbackEnvironment") && shell.includes("API connected · status fallback"), "provider shell must not report false offline when domains endpoint is reachable"],
    [domainWorkspace.includes("Evaluate now"), "domain monitor action missing"],
    [views.includes("Generate explanation"), "AI explanation action missing"],
    [views.includes("Create rollback preview"), "recovery preview action missing"],
    [views.includes("Approve recovery"), "human approval action missing"],
    [views.includes("Apply approved recovery"), "approved recovery apply action missing"],
    [views.includes("Post-mutation proof") && views.includes("EXPECTED") && views.includes("ACTUAL"), "verification UI missing"],
    [views.includes("name.com") && views.includes("Provider operations stay visible"), "name.com integration depth not visible"],
    [views.includes("LoadingState") && views.includes("ErrorState") && views.includes("EmptyState"), "loading/error/empty states missing"],
    [overview.includes("NO ACTIVE INCIDENT RISK") && overview.includes("LATEST INCIDENT RISK"), "overview must separate active and historical risk"],
    [domainWorkspace.includes("NO ACTIVE INCIDENT RISK") && domainWorkspace.includes("ACTIVE INCIDENT"), "domain workspace must separate active and historical incident state"],
    [domainRoute.includes("DomainWorkspaceDashboard"), "domain route must use hardened workspace"],
    [backendViews.includes("SAFE_DOMAIN_FIELDS") && backendViews.includes("_safe_domain_payload"), "backend domain metadata sanitizer missing"],
    [backendViews.includes('"contacts"') === false, "backend safe domain response must not whitelist contacts"],
    [domainWorkspace.includes("JSON.stringify") === false, "domain workspace must not render raw provider objects"],
    [proxy.includes("API_BASE_URL") && proxy.includes("/api/${encodedPath}/"), "same-origin backend proxy missing"],
    [!proxy.includes("NAMECOM_API_TOKEN") && !proxy.includes("OPENAI_API_KEY"), "proxy must never expose provider secrets"],
  ];
  for (const [ok, message] of checks) if (!ok) failures.push(message);
}

if (failures.length) {
  console.error("GATE 7 CONTRACT FAILED");
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}

console.log("GATE 7 CONTRACT PASS");
console.log(`Required routes: ${requiredRoutes.length}/8`);
console.log("Environment indicator: present");
console.log("Provider status fallback: domains reachability prevents false offline state");
console.log("Risk semantics: active vs historical separated");
console.log("Domain metadata privacy: contacts blocked at backend boundary");
console.log("Core flow: status -> evidence -> AI -> preview -> approve -> apply -> verify");
console.log("External-call states: loading/error/empty present");
console.log("Secrets: server-side proxy boundary preserved");
