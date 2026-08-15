import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { EmptyState } from "@/components/ui/EmptyState";
import { DealCard } from "@/features/deals/DealCard";
import { FilterBar } from "@/features/discovery/FilterBar";
import { api } from "@/lib/api/client";
import { titleCaseSlug } from "@/lib/format";

export const dynamic = "force-dynamic";

const ALLOWED = new Set(["los-angeles"]);

type Props = { params: Promise<{ city: string }>; searchParams: Promise<{ neighborhood?: string; active_now?: string; offering?: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { city } = await params;
  if (!ALLOWED.has(city)) return {};
  const name = titleCaseSlug(city);
  return {
    title: `Deals in ${name}`,
    description: `Good food and drink deals in ${name}.`,
    alternates: { canonical: `/${city}` },
  };
}

export default async function CityPage({ params, searchParams }: Props) {
  const { city } = await params;
  if (!ALLOWED.has(city)) notFound();
  const query = await searchParams;
  const cityName = titleCaseSlug(city);
  const deals = await api.listDeals({
    city: cityName,
    neighborhood: query.neighborhood,
    food_or_drink: query.offering as "food" | "drink" | "both" | undefined,
    active_now: query.active_now === "1" || undefined,
  });
  return (
    <div>
      <h1 className="font-display text-5xl">{cityName}</h1>
      <p className="mt-3 text-muted">What’s good in {cityName} right now.</p>
      <div className="mt-6">
        <FilterBar
          city={cityName}
          neighborhood={query.neighborhood}
          activeNow={query.active_now === "1"}
          offering={query.offering}
        />
      </div>
      {deals.items.length === 0 ? (
        <div className="mt-10">
          <EmptyState title={`No deals in ${cityName} yet`} body="We’re still gathering the good stuff." />
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
