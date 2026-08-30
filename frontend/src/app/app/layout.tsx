import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { ProductShell } from "@/components/ProductShell";
import type { AuthSession, AuthUser } from "@/lib/auth";
import "./product.css";
import "./p6.css";
import "./p7.css";

export const dynamic = "force-dynamic";

async function requireWorkspaceSession(): Promise<AuthUser> {
  const store = await cookies();
  const cookieHeader = store
    .getAll()
    .map(({ name, value }) => `${name}=${value}`)
    .join("; ");

  if (!cookieHeader) redirect("/login");

  const base = (process.env.API_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000")
    .replace(/\/$/, "");

  let response: Response;
  try {
    response = await fetch(`${base}/api/auth/me/`, {
      headers: {
        accept: "application/json",
        cookie: cookieHeader,
      },
      cache: "no-store",
      signal: AbortSignal.timeout(5000),
    });
  } catch {
    redirect("/login");
  }

  if (!response.ok) redirect("/login");

  let session: AuthSession;
  try {
    session = await response.json() as AuthSession;
  } catch {
    redirect("/login");
  }
  if (!session.authenticated || !session.user) redirect("/login");
  return session.user;
}

export default async function AppLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  const user = await requireWorkspaceSession();
  const viewerMode = user.role === "VIEWER";

  return (
    <div className={viewerMode ? "viewer-workspace" : undefined}>
      {viewerMode ? (
        <style>{`.viewer-workspace .product-content button { display: none !important; }`}</style>
      ) : null}
      <ProductShell user={user}>{children}</ProductShell>
    </div>
  );
}
