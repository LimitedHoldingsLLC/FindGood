import Link from "next/link";

import { analytics } from "@/lib/analytics";
import { titleCaseKey } from "@/lib/format";

import type { MapPin } from "./types";

export function ResultCard({
  pin,
  selected,
  hovered,
  returnHref,
  onSelect,
  onHover,
}: {
  pin: MapPin;
  selected: boolean;
  hovered: boolean;
  returnHref: string;
  onSelect: () => void;
  onHover: (on: boolean) => void;
}) {
  const offer = pin.best_offer;
  return (
    <article
      id={`map-card-${pin.id}`}
      className={`rounded-2xl border p-4 transition ${
        selected || hovered ? "border-terracotta bg-white shadow-card" : "border-ink/10 bg-card"
      }`}
      onMouseEnter={() => onHover(true)}
      onMouseLeave={() => onHover(false)}
    >
      <button type="button" className="w-full text-left" onClick={onSelect}>
        <p className="text-xs uppercase tracking-[0.16em] text-muted">{pin.neighborhood ?? titleCaseKey(pin.category)}</p>
        <h2 className="mt-1 font-display text-2xl leading-tight">{pin.name}</h2>
        {offer ? (
          <p className="mt-2 text-sm">
            <span className="font-medium">{offer.label}</span>
            <span className="text-muted"> · {offer.title}</span>
          </p>
        ) : null}
        {offer ? (
          <p className="mt-1 text-xs text-muted">
            {offer.availability_label}
            {offer.freshness === "fresh" ? " · Fresh" : offer.freshness === "aging" ? " · Aging" : ""}
            {offer.extra_offer_count ? ` · +${offer.extra_offer_count} more` : ""}
          </p>
        ) : null}
      </button>
      <div className="mt-3 flex gap-3 text-sm">
        <Link
          className="text-terracotta underline-offset-4 hover:underline"
          href={`/venues/${pin.slug}?from=${encodeURIComponent(returnHref)}`}
          onClick={() => analytics.track("map_to_detail_conversion", { slug: pin.slug })}
        >
          Details
        </Link>
        <a
          className="text-muted underline-offset-4 hover:underline"
          href={`https://www.google.com/maps/dir/?api=1&destination=${pin.lat},${pin.lng}`}
        >
          Directions
        </a>
      </div>
    </article>
  );
}
