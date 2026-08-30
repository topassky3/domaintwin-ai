"use client";

import { useEffect, useState } from "react";

type HealthState = "checking" | "online" | "offline";

export function ApiStatus() {
  const [state, setState] = useState<HealthState>("checking");

  useEffect(() => {
    fetch("/api/domaintwin/health", { signal: AbortSignal.timeout(2500) })
      .then((response) => {
        if (!response.ok) throw new Error("API unavailable");
        return response.json();
      })
      .then(() => setState("online"))
      .catch(() => setState("offline"));
  }, []);

  return (
    <span className={`api-status api-status--${state}`} aria-live="polite">
      <span className="status-dot" aria-hidden="true" />
      {state === "checking" ? "API CHECKING" : state === "online" ? "API ONLINE" : "API OFFLINE"}
    </span>
  );
}
