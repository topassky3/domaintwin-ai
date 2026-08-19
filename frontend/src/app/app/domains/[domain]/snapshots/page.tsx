import { SnapshotsView } from "@/components/ProductViews";

export default async function SnapshotsPage({ params }: { params: Promise<{ domain: string }> }) {
  const { domain } = await params;
  return <SnapshotsView domain={decodeURIComponent(domain)} />;
}
