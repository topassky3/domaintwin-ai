export interface AuthUser {
  id: number;
  username: string;
  email: string;
  isStaff: boolean;
  isSuperuser: boolean;
}

export interface AuthSession {
  authenticated: boolean;
  user?: AuthUser;
  remember?: boolean;
}

interface ApiErrorShape {
  error?: { message?: string; status?: number };
}

let csrfTokenCache: string | null = null;

async function parseJson(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

function messageFor(response: Response, payload: unknown): string {
  const shaped = payload as ApiErrorShape | null;
  return shaped?.error?.message ?? `DomainTwin authentication returned HTTP ${response.status}.`;
}

export async function getCsrfToken(force = false): Promise<string> {
  if (!force && csrfTokenCache) return csrfTokenCache;

  const response = await fetch("/api/domaintwin/auth/csrf/", {
    method: "GET",
    credentials: "same-origin",
    cache: "no-store",
  });
  const payload = await parseJson(response) as { csrfToken?: string } | null;
  if (!response.ok || !payload?.csrfToken) {
    throw new Error(messageFor(response, payload));
  }

  csrfTokenCache = payload.csrfToken;
  return csrfTokenCache;
}

export async function signIn(
  identifier: string,
  password: string,
  remember: boolean,
): Promise<AuthSession> {
  const csrfToken = await getCsrfToken();
  const response = await fetch("/api/domaintwin/auth/login/", {
    method: "POST",
    credentials: "same-origin",
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": csrfToken,
    },
    body: JSON.stringify({ identifier, password, remember }),
  });
  const payload = await parseJson(response);
  if (!response.ok) throw new Error(messageFor(response, payload));

  // Django rotates the CSRF secret when authentication succeeds. Force the next
  // mutation to bootstrap a token that belongs to the authenticated session.
  csrfTokenCache = null;
  return payload as AuthSession;
}

export async function currentSession(): Promise<AuthSession> {
  const response = await fetch("/api/domaintwin/auth/me/", {
    method: "GET",
    credentials: "same-origin",
    cache: "no-store",
  });
  const payload = await parseJson(response);
  if (!response.ok) throw new Error(messageFor(response, payload));
  return payload as AuthSession;
}

export async function signOut(): Promise<void> {
  const csrfToken = await getCsrfToken(true);
  const response = await fetch("/api/domaintwin/auth/logout/", {
    method: "POST",
    credentials: "same-origin",
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": csrfToken,
    },
    body: "{}",
  });
  const payload = await parseJson(response);
  csrfTokenCache = null;
  if (!response.ok) throw new Error(messageFor(response, payload));
}
