import { RecoveryDashboard } from "@/components/RecoveryDashboard";

type RecoveryPageProps = {
  searchParams: Promise<{ domain?: string; incident?: string }>;
};

export default async function RecoveryPage({ searchParams }: RecoveryPageProps) {
  const params = await searchParams;
  const parsedIncident = Number(params.incident ?? "");
  const incidentId = Number.isInteger(parsedIncident) && parsedIncident > 0 ? parsedIncident : null;

  return (
    <RecoveryDashboard
      initialDomain={params.domain ?? ""}
      initialIncidentId={incidentId}
    />
  );
}
