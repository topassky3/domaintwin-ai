import { DomainDetailView } from "@/components/ProductViews";

export default async function DomainPage({ params }: { params: Promise<{ domain: string }> }) {
  const { domain } = await params;
  return <DomainDetailView domain={decodeURIComponent(domain)} />;
}
