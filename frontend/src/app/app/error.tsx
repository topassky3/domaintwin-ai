"use client";

import Link from "next/link";

export default function WorkspaceError({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <div className="p7-workspace-fallback">
      <div>
        <span className="eyebrow">WORKSPACE RECOVERY</span>
        <h2>The live workspace hit an unexpected error.</h2>
        <p>DomainTwin kept the failure inside the private workspace. Retry the current view, return to Overview, or continue with the safe public walkthrough while the backend/provider recovers.</p>
        <div className="p7-workspace-fallback-actions">
          <button className="button button--primary" type="button" onClick={reset}>Retry view</button>
          <Link className="button button--secondary" href="/app/overview">Back to Overview</Link>
          <Link className="button button--secondary" href="/demo">Open safe demo</Link>
        </div>
      </div>
    </div>
  );
}
