import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { EmptyState } from "@/components/ui/EmptyState";
import { DealCard } from "@/features/deals/DealCard";
import { FilterBar } from "@/features/discovery/FilterBar";
import { dealQueryFromSearch, filterStateFromSearch, type DiscoverySearch } from "@/features/discovery/query";
import { api } from "@/lib/api/client";
import { titleCaseSlug } from "@/lib/format";
import { NEIGHBORHOODS } from "@/lib/location";

export const dynamic = "force-dynamic";

type Props = {
  params: Promise<{ city: string; neighborhood: string }>;
  searchParams: Promise<DiscoverySearch>;
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { city, neighborhood } = await params;
  const cityName = titleCaseSlug(city);
  const hood = titleCaseSlug(neighborhood);
  return {
    title: `${hood}, ${cityName} deals`,
    alternates: { canonical: `/${city}/${neighborhood}` },
  };
}

export default async function NeighborhoodPage({ params, searchParams }: Props) {
  const { city, neighborhood } = await params;
  if (city !== "los-angeles") notFound();
  const hood = titleCaseSlug(neighborhood);
  if (!NEIGHBORHOODS.includes(hood)) notFound();
  const query = await searchParams;
  const deals = await api.listDeals(dealQueryFromSearch({ ...query, neighborhood: hood }, "Los Angeles"));
  return (
    <div>
      <p className="text-sm uppercase tracking-[0.2em] text-muted">Los Angeles</p>
      <h1 className="mt-2 font-display text-5xl">{hood}</h1>
      <div className="mt-6">
        <FilterBar city="Los Angeles" state={filterStateFromSearch({ ...query, neighborhood: hood })} />
      </div>
      {deals.items.length === 0 ? (
        <div className="mt-10">
          <EmptyState title={`Quiet in ${hood}`} body="No published deals for this neighborhood yet." />
        </div>
      ) : (
        <div className="mt-8 grid gap-4 md:grid-cols-2">
          {deals.items.map((deal) => (
            <DealCard key={deal.id} deal={deal} />
          ))}
        </div>
      )}
    </div>
  );
}
