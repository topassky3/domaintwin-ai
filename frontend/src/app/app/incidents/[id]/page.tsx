import { IncidentDetailView } from "@/components/ProductViews";

export default async function IncidentPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <IncidentDetailView incidentId={Number(id)} />;
}
