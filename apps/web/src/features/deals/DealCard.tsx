import Link from "next/link";

import { StatusBadge } from "@/components/ui/StatusBadge";
import type { Deal } from "@/lib/api/types";
import { priceLevelLabel, primaryPrice, titleCaseKey } from "@/lib/format";

const KIND_LABEL: Record<string, string> = {
  food: "Food",
  drink: "Drinks",
  both: "Food + drinks",
};

export function DealCard({ deal }: { deal: Deal }) {
  const price = primaryPrice(deal.items);
  return (
    <Link
      href={`/venues/${deal.venue.slug}`}
      className="group block rounded-3xl border border-ink/10 bg-card p-5 shadow-card transition hover:-translate-y-0.5 hover:border-terracotta/40"
    >
      <div className="flex items-start justify-between gap-3">
        <p className="text-xs uppercase tracking-[0.18em] text-muted">
          {deal.location.neighborhood ?? deal.location.city}
        </p>
        <StatusBadge status={deal.availability.status} label={deal.availability.label} />
      </div>
      <h3 className="mt-3 font-display text-2xl leading-tight group-hover:text-terracotta">
        {deal.title}
      </h3>
      <p className="mt-1 text-sm text-muted">
        {deal.venue.name}
        {priceLevelLabel(deal.venue.price_level) ? ` · ${priceLevelLabel(deal.venue.price_level)}` : ""}
        {deal.venue.cuisines?.[0] ? ` · ${titleCaseKey(deal.venue.cuisines[0])}` : ""}
      </p>
      {deal.description ? (
        <p className="mt-3 line-clamp-2 text-sm leading-relaxed text-ink/80">{deal.description}</p>
      ) : null}
      <div className="mt-5 flex items-end justify-between gap-3">
        <div>
          <p className="font-display text-2xl">{price.deal ?? "See menu"}</p>
          <p className="text-xs text-muted">
            {price.normal ? <span className="line-through">{price.normal}</span> : null}
            {price.savings ? <span className="ml-2 text-forest">{price.savings}</span> : null}
          </p>
        </div>
        <div className="text-right text-xs text-muted">
          <p>{KIND_LABEL[deal.offering_kind]}</p>
          <p>{deal.verification.label}</p>
          {deal.distance_km != null ? <p>{deal.distance_km} km</p> : null}
        </div>
      </div>
    </Link>
  );
}
