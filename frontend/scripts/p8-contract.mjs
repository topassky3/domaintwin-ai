import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const repoRoot = path.resolve(root, "..");
const read = (relativePath) => fs
  .readFileSync(path.join(repoRoot, relativePath), "utf8")
  .replace(/\r\n/g, "\n");

const compose = read("compose.yaml");
const caddy = read("deploy/Caddyfile");
const deployEnv = read("deploy/.env.example");
const backendDocker = read("backend/Dockerfile");
const backendEntrypoint = read("backend/docker-entrypoint.sh");
const backendRequirements = read("backend/requirements.txt");
const settings = read("backend/config/settings.py");
const frontendDocker = read("frontend/Dockerfile");
const nextConfig = read("frontend/next.config.ts");
const ci = read(".github/workflows/ci.yml");
const doc = read("docs/P8_DEPLOY.md");

const serviceBlock = (name) => {
  const marker = `  ${name}:`;
  const start = compose.indexOf(marker);
  if (start < 0) return "";
  const next = compose.indexOf("\n  ", start + marker.length);
  return next < 0 ? compose.slice(start) : compose.slice(start, next);
};

const frontendService = serviceBlock("frontend");
const backendService = serviceBlock("backend");
const monitorService = serviceBlock("monitor");
const caddyService = serviceBlock("caddy");

const checks = [
  [backendService && monitorService && frontendService && caddyService, "P8 defines the four-service single-host hackathon runtime"],
  [!backendService.includes("ports:") && !frontendService.includes("ports:") && !monitorService.includes("ports:") && caddyService.includes('"80:80"') && caddyService.includes('"443:443"'), "only Caddy publishes host HTTP/HTTPS ports"],
  [backendService.includes("env_file:") && monitorService.includes("env_file:") && !frontendService.includes("env_file:") && frontendService.includes("API_BASE_URL: http://backend:8000"), "provider secret environment is backend/monitor-only"],
  [backendService.includes("domaintwin_data:/data") && monitorService.includes("domaintwin_data:/data") && settings.includes('os.getenv("DJANGO_DB_PATH"') && settings.includes('DJANGO_DB_TIMEOUT_SECONDS'), "backend and monitor share one configurable persistent SQLite volume with timeout"],
  [backendEntrypoint.includes("python manage.py migrate --noinput") && backendEntrypoint.includes("until python manage.py migrate --check") && backendEntrypoint.includes("monitor_domaintwin --loop"), "web owns migrations and monitor waits before polling"],
  [backendDocker.includes("FROM python:3.12-slim") && backendDocker.includes("ENTRYPOINT") && backendRequirements.includes("gunicorn==23.0.0"), "backend image uses Python 3.12 and pinned Gunicorn"],
  [nextConfig.includes('output: "standalone"') && frontendDocker.includes("FROM node:20-alpine") && frontendDocker.includes(".next/standalone") && frontendDocker.includes('CMD ["node", "server.js"]'), "frontend image uses Node 20 and Next standalone output"],
  [caddy.includes("reverse_proxy frontend:3000") && caddy.includes("{$DOMAIN_TWIN_HOST:localhost}"), "Caddy terminates the public host and proxies only to Next.js"],
  [deployEnv.includes("DJANGO_DEBUG=0") && deployEnv.includes("DJANGO_SECURE_COOKIES=1") && deployEnv.includes("NAMECOM_ENVIRONMENT=sandbox") && deployEnv.includes("NAMECOM_ALLOW_PRODUCTION_MUTATIONS=0"), "deployment template defaults to secure cookies, debug off and sandbox-only provider mutation"],
  [settings.includes("CSRF_TRUSTED_ORIGINS") && deployEnv.includes("DJANGO_CSRF_TRUSTED_ORIGINS=https://"), "HTTPS CSRF trusted origin is explicit deployment configuration"],
  [ci.includes("P8 deploy contract") && ci.includes("npm run p8:contract") && ci.includes("docker compose") && ci.includes("build backend frontend"), "CI validates Compose and actually builds both application images"],
  [doc.includes("P8 acceptance criteria") && doc.includes("Judge-day preflight") && doc.includes("demo_readiness --organization") && doc.includes("Explicitly deferred after the hackathon"), "deployment runbook includes bootstrap, live preflight and explicit post-hackathon deferrals"],
];

const failed = checks.filter(([ok]) => !ok);
if (failed.length > 0) {
  console.error("P8 CONTRACT FAIL");
  for (const [, message] of failed) console.error(`- ${message}`);
  process.exit(1);
}

console.log("P8 CONTRACT PASS");
for (const [, message] of checks) console.log(`- ${message}`);
