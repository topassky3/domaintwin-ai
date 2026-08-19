export type Environment = "sandbox" | "production" | string;

export interface ApiErrorShape {
  error?: { message?: string; status?: number; retryable?: boolean; details?: unknown };
}

export interface NameComStatus {
  status: string;
  provider: string;
  environment: Environment;
  apiBaseUrl?: string;
  username?: string;
  serverTime?: string;
}

export interface DomainSummary {
  domainName?: string;
  domain?: string;
  name?: string;
  expireDate?: string;
  createDate?: string;
  locked?: boolean;
  autorenewEnabled?: boolean;
  [key: string]: unknown;
}

export interface DomainsResponse {
  environment: Environment;
  domains: DomainSummary[];
  nextPage?: number;
  lastPage?: number;
}

export interface DnsRecord {
  id?: number;
  type: string;
  host: string;
  answer: string;
  ttl?: number;
  priority?: number;
}

export interface RecordsResponse {
  environment: Environment;
  records: DnsRecord[];
}

export interface DiffChange {
  state: "ADDED" | "REMOVED" | "MODIFIED" | "UNCHANGED" | string;
  before: DnsRecord | null;
  after: DnsRecord | null;
}

export interface DiffResponse {
  domainName: string;
  baselineSnapshotId: number;
  baselineVersion: number;
  baselineFingerprint: string;
  liveFingerprint: string;
  driftDetected: boolean;
  summary: Record<string, number>;
  changes: DiffChange[];
}

export interface HealthObservation {
  id?: number;
  domainName?: string;
  dnsResolution?: { ok?: boolean; addresses?: string[]; error?: string | null };
  http?: { ok?: boolean; statusCode?: number | null; latencyMs?: number | null; error?: string | null };
  https?: { ok?: boolean; statusCode?: number | null; latencyMs?: number | null; error?: string | null };
  availabilityOk?: boolean;
  availabilityFailed?: boolean;
  checkedAt?: string;
}

export interface RiskFactor {
  ruleId?: string;
  points?: number;
  reason?: string;
  state?: string | null;
  recordType?: string | null;
  host?: string | null;
  before?: DnsRecord | null;
  after?: DnsRecord | null;
}

export interface TimelineEvent {
  sequence: number;
  eventType: string;
  payload?: Record<string, unknown>;
  occurredAt: string;
}

export interface Incident {
  id: number;
  domainName: string;
  status: "OPEN" | "RESOLVED" | string;
  baselineSnapshotId: number;
  score: number;
  severity: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL" | string;
  factorCount: number;
  factors: RiskFactor[];
  evidence?: Record<string, unknown>;
  evidenceFingerprint: string;
  openedAt: string;
  lastSeenAt: string;
  resolvedAt?: string | null;
  timeline?: TimelineEvent[];
}

export interface MonitorStatus {
  domainName: string;
  state: "HEALTHY" | "DEGRADED" | "INCIDENT" | string;
  activeIncident: Incident | null;
  latestHealth: HealthObservation | null;
}

export interface EvaluationResponse {
  domainName: string;
  state: string;
  driftDetected: boolean;
  diff: { summary: Record<string, number>; changes: DiffChange[] };
  health: HealthObservation;
  unknownDestination: boolean;
  risk: { score: number; severity: string; factors: RiskFactor[] };
  incidentCreated: boolean;
  incident: Incident | null;
}

export interface Snapshot {
  id: number;
  domainName: string;
  version: number;
  records: DnsRecord[];
  recordCount: number;
  fingerprint: string;
  isKnownGood: boolean;
  createdAt: string;
}

export interface SnapshotsResponse {
  domainName: string;
  knownGoodSnapshotId: number | null;
  snapshots: Snapshot[];
  totalCount: number;
}

export interface RecoveryOperation {
  action: "CREATE" | "UPDATE" | "DELETE" | string;
  recordId?: number | null;
  before?: DnsRecord | null;
  after?: DnsRecord | null;
  current?: DnsRecord | null;
  desired?: DnsRecord | null;
  [key: string]: unknown;
}

export interface RecoveryAuditEvent {
  sequence: number;
  eventType: string;
  payload?: Record<string, unknown>;
  occurredAt: string;
}

export interface RecoveryPlan {
  id: number;
  domainName: string;
  status: "PREVIEW" | "APPROVED" | "APPLYING" | "RECOVERED" | "PARTIAL" | "FAILED" | "STALE" | string;
  baselineSnapshotId: number;
  baselineVersion: number;
  incidentId?: number | null;
  liveFingerprintBefore: string;
  targetFingerprint: string;
  planFingerprint: string;
  operationCount: number;
  operations: RecoveryOperation[];
  operationResults: Array<Record<string, unknown>>;
  verification: Record<string, unknown>;
  requiresApproval: boolean;
  canApply: boolean;
  approvedAt?: string | null;
  appliedAt?: string | null;
  verifiedAt?: string | null;
  createdAt: string;
  updatedAt: string;
  audit?: RecoveryAuditEvent[];
}

export interface AIAnalysis {
  label: string;
  status: "NOT_GENERATED" | "GENERATED" | "UNAVAILABLE" | "INVALID" | string;
  aiAvailable: boolean;
  cached: boolean;
  explanationId?: number | null;
  incidentId: number;
  evidenceFingerprint: string;
  provider?: string;
  model?: string;
  probableCause?: string | null;
  affectedService?: string | null;
  evidenceRefs?: string[];
  evidence?: Array<{ id: string; source: string; fact: string; data?: unknown }>;
  recommendedAction?: string | null;
  confidence?: { level?: string; reason?: string };
  requestId?: string | null;
  latencyMs?: number | null;
  error?: string | null;
  generatedAt?: string;
  safety?: {
    factsComeFromDeterministicEvidence?: boolean;
    aiCanMutateDns?: boolean;
    humanApprovalStillRequired?: boolean;
  };
}

export function domainNameOf(domain: DomainSummary): string {
  return String(domain.domainName ?? domain.domain ?? domain.name ?? "");
}

export function encodeDomain(domain: string): string {
  return encodeURIComponent(domain);
}

export function compactFingerprint(value?: string | null): string {
  if (!value) return "—";
  return `${value.slice(0, 10)}…${value.slice(-8)}`;
}

export function formatDate(value?: string | null): string {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const normalized = path.replace(/^\/+/, "");
  const headers = new Headers(init?.headers);
  if (init?.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");

  const response = await fetch(`/api/domaintwin/${normalized}`, {
    ...init,
    headers,
    cache: "no-store",
  });

  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (!response.ok) {
    const shaped = payload as ApiErrorShape | null;
    const message = shaped?.error?.message ?? `DomainTwin API returned HTTP ${response.status}.`;
    throw new Error(message);
  }

  return payload as T;
}
