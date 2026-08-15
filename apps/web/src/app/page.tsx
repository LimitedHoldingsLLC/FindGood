import Link from "next/link";

import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { DealCard } from "@/features/deals/DealCard";
import { FilterBar } from "@/features/discovery/FilterBar";
import { api } from "@/lib/api/client";
import type { OfferingKind } from "@/lib/api/types";

export const dynamic = "force-dynamic";

type Search = {
  neighborhood?: string;
  active_now?: string;
  offering?: string;
};

export default async function HomePage({ searchParams }: { searchParams: Promise<Search> }) {
  const params = await searchParams;
  const offering = params.offering as OfferingKind | undefined;
  try {
    const deals = await api.listDeals({
      city: "Los Angeles",
      neighborhood: params.neighborhood,
      food_or_drink: offering,
      active_now: params.active_now === "1" || undefined,
    });
    return (
      <div>
        <section className="max-w-3xl pb-10 pt-4">
          <p className="text-sm uppercase tracking-[0.22em] text-terracotta">Los Angeles</p>
          <h1 className="mt-3 font-display text-5xl leading-[1.05] md:text-6xl">What’s good near you?</h1>
          <p className="mt-4 max-w-xl text-lg text-muted">
            Genuinely good food and drink, at unusually good prices, happening around the city right now.
          </p>
        </section>
        <FilterBar
          city="Los Angeles"
          neighborhood={params.neighborhood}
          activeNow={params.active_now === "1"}
          offering={params.offering}
        />
        {deals.items.length === 0 ? (
          <div className="mt-10">
            <EmptyState
              title="No deals match that filter"
              body="Try another neighborhood, or look at everything happening in Los Angeles."
              action={
                <Link href="/" className="rounded-full bg-ink px-4 py-2 text-sm text-paper">
                  Clear filters
                </Link>
              }
            />
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
  } catch {
    return <ErrorState />;
  }
}
