import { DomainWorkspaceDashboard } from "@/components/DomainWorkspaceDashboard";

export default async function DomainPage({ params }: { params: Promise<{ domain: string }> }) {
  const { domain } = await params;
  return <DomainWorkspaceDashboard domain={decodeURIComponent(domain)} />;
}
