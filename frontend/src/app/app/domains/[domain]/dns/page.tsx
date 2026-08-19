import { DnsView } from "@/components/ProductViews";

export default async function DnsPage({ params }: { params: Promise<{ domain: string }> }) {
  const { domain } = await params;
  return <DnsView domain={decodeURIComponent(domain)} />;
}
