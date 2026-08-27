import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(scriptDir, "../..");

const read = (relativePath) =>
  fs.readFileSync(path.join(repoRoot, relativePath), "utf8");

const workflow = read(".github/workflows/ci.yml");
const gitignore = read(".gitignore");
const p1Doc = read("docs/P1_ENGINEERING_BASELINE.md");
const packageJson = JSON.parse(read("frontend/package.json"));
const packageLock = JSON.parse(read("frontend/package-lock.json"));

const directDependencies = {
  ...(packageJson.dependencies ?? {}),
  ...(packageJson.devDependencies ?? {}),
};
const exactVersion = /^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$/;
const dependencyEntries = Object.entries(directDependencies);
const allDirectDependenciesPinned = dependencyEntries.every(([, version]) =>
  exactVersion.test(version),
);
const lockResolvesPinnedVersions = dependencyEntries.every(([name, version]) =>
  packageLock.packages?.[`node_modules/${name}`]?.version === version,
);

const checkoutPin =
  "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1";
const setupPythonPin =
  "actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97";
const setupNodePin =
  "actions/setup-node@820762786026740c76f36085b0efc47a31fe5020";

const checks = [
  [workflow.includes("pull_request:"), "CI runs on pull requests"],
  [workflow.includes("push:"), "CI runs on pushes"],
  [workflow.includes("workflow_dispatch:"), "CI supports manual dispatch"],
  [workflow.includes("branches: [main]"), "CI targets main"],
  [workflow.includes('python-version: "3.12"'), "Python 3.12 is explicit"],
  [workflow.includes('node-version: "20"'), "Node.js 20 application runtime is explicit"],
  [workflow.split(checkoutPin).length - 1 === 2, "checkout is pinned to the verified v7.0.1 commit"],
  [workflow.includes(setupPythonPin), "setup-python is pinned to the verified v7.0.0 commit"],
  [workflow.includes(setupNodePin), "setup-node is pinned to the verified v7.0.0 commit"],
  [!workflow.includes("actions/checkout@v4"), "deprecated checkout v4 action is absent"],
  [!workflow.includes("actions/setup-python@v5"), "deprecated setup-python v5 action is absent"],
  [!workflow.includes("actions/setup-node@v4"), "deprecated setup-node v4 action is absent"],
  [workflow.includes("python manage.py makemigrations --check --dry-run"), "migration drift is checked"],
  [workflow.includes("python manage.py check"), "Django system check is automated"],
  [workflow.includes("python manage.py test core"), "backend regression is automated"],
  [workflow.includes("python -m pip check"), "Python dependency graph is validated"],
  [workflow.includes("Backend dependency pins verified"), "backend direct pins are verified in CI"],
  [workflow.includes("run: npm ci"), "frontend uses lockfile-exact npm ci"],
  [workflow.includes("npm run gate7:contract"), "Gate 7 contract remains in CI"],
  [workflow.includes("npm run gate8:contract"), "Gate 8 contract remains in CI"],
  [workflow.includes("npm run gate9:contract"), "Gate 9 contract remains in CI"],
  [workflow.includes("npm run gate10:contract"), "Gate 10 contract remains in CI"],
  [workflow.includes("npm run gate11:contract"), "Gate 11 contract remains in CI"],
  [workflow.includes("npm run p1:contract"), "P1 contract validates CI itself"],
  [workflow.includes("npm run typecheck"), "TypeScript is automated"],
  [workflow.includes("npm run build"), "production build is automated"],
  [workflow.includes("NAMECOM_ENVIRONMENT: sandbox"), "CI is sandbox-only"],
  [workflow.includes('NAMECOM_ALLOW_MUTATIONS: "0"'), "DNS mutation is disabled in CI"],
  [workflow.includes('NAMECOM_ALLOW_PRODUCTION_MUTATIONS: "0"'), "production mutation is disabled in CI"],
  [workflow.includes('NAMECOM_ALLOW_DOMAIN_REGISTRATION: "0"'), "domain registration is disabled in CI"],
  [workflow.includes("AI_PROVIDER: disabled"), "AI is disabled in CI"],
  [workflow.includes("ci-not-a-real-token"), "CI uses an explicitly fake provider token"],
  [!workflow.includes("secrets.NAMECOM"), "CI does not require name.com GitHub secrets"],
  [!workflow.includes("secrets.OPENAI"), "CI does not require AI GitHub secrets"],
  [gitignore.includes("*.tsbuildinfo"), "TypeScript build-info cache is ignored"],
  [p1Doc.includes("P1-A acceptance criteria"), "P1-A acceptance criteria are documented"],
  [p1Doc.includes("P1-D acceptance criteria"), "P1-D acceptance criteria are documented"],
  [packageLock.lockfileVersion === 3, "frontend uses lockfile v3"],
  [allDirectDependenciesPinned, "frontend direct dependencies use exact versions"],
  [!Object.values(directDependencies).includes("latest"), "frontend package.json contains no latest tags"],
  [lockResolvesPinnedVersions, "package-lock resolves every pinned direct dependency exactly"],
];

const failed = checks.filter(([ok]) => !ok);

if (failed.length > 0) {
  console.error("P1 CONTRACT FAIL");
  for (const [, message] of failed) {
    console.error(`- ${message}`);
  }
  process.exit(1);
}

console.log("P1 CONTRACT PASS");
for (const [, message] of checks) {
  console.log(`- ${message}`);
}
