import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const METHODS_WITH_BODY = new Set(["POST", "PUT", "PATCH", "DELETE"]);

async function proxy(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  const { path } = await context.params;
  const base = (process.env.API_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000")
    .replace(/\/$/, "");
  const encodedPath = path.map((segment) => encodeURIComponent(segment)).join("/");
  const target = `${base}/api/${encodedPath}/${request.nextUrl.search}`;

  const headers = new Headers();
  const contentType = request.headers.get("content-type");
  if (contentType) headers.set("content-type", contentType);
  headers.set("accept", "application/json");

  const cookie = request.headers.get("cookie");
  if (cookie) headers.set("cookie", cookie);

  const csrfToken = request.headers.get("x-csrftoken");
  if (csrfToken) headers.set("x-csrftoken", csrfToken);

  const body = METHODS_WITH_BODY.has(request.method) ? await request.text() : undefined;

  try {
    const upstream = await fetch(target, {
      method: request.method,
      headers,
      body: body || undefined,
      cache: "no-store",
      signal: AbortSignal.timeout(20000),
    });

    const text = await upstream.text();
    const responseHeaders = new Headers({
      "content-type": upstream.headers.get("content-type") ?? "application/json",
      "cache-control": "no-store",
    });

    const cookieAwareHeaders = upstream.headers as Headers & {
      getSetCookie?: () => string[];
    };
    const setCookies = cookieAwareHeaders.getSetCookie?.() ?? [];
    if (setCookies.length > 0) {
      for (const value of setCookies) responseHeaders.append("set-cookie", value);
    } else {
      const setCookie = upstream.headers.get("set-cookie");
      if (setCookie) responseHeaders.append("set-cookie", setCookie);
    }

    return new NextResponse(text || null, {
      status: upstream.status,
      headers: responseHeaders,
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Backend unavailable";
    return NextResponse.json(
      { error: { message: `DomainTwin backend unavailable: ${message}`, status: 502, retryable: true } },
      { status: 502, headers: { "cache-control": "no-store" } },
    );
  }
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const DELETE = proxy;
export const PATCH = proxy;
