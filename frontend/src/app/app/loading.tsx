export default function WorkspaceLoading() {
  return (
    <div className="p7-workspace-fallback">
      <div>
        <span className="product-spinner" />
        <span className="eyebrow">LIVE WORKSPACE</span>
        <h2>Loading verified DomainTwin state…</h2>
        <p>Session, tenant context and live control-plane data are being resolved.</p>
      </div>
    </div>
  );
}
