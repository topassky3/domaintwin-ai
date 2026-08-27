import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { ProductShell } from "@/components/ProductShell";
import "./product.css";

export const dynamic = "force-dynamic";

async function requireWorkspaceSession() {
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
}

export default async function AppLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  await requireWorkspaceSession();
  return <ProductShell>{children}</ProductShell>;
}
