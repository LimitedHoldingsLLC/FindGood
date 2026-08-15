import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { DealCard } from "@/features/deals/DealCard";
import { ApiError, api } from "@/lib/api/client";
import { maps } from "@/lib/maps";

export const dynamic = "force-dynamic";

type Props = { params: Promise<{ slug: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  try {
    const venue = await api.getVenue(slug);
    return {
      title: venue.name,
      description: venue.description ?? `Deals at ${venue.name}`,
      alternates: { canonical: `/venues/${venue.slug}` },
    };
  } catch {
    return { title: "Venue" };
  }
}

export default async function VenuePage({ params }: Props) {
  const { slug } = await params;
  try {
    const venue = await api.getVenue(slug);
    const location = venue.locations[0];
    const directions = location
      ? maps.directionsUrl(location.latitude, location.longitude, venue.name)
      : null;
    return (
      <article>
        <p className="text-sm uppercase tracking-[0.2em] text-terracotta">
          {location?.neighborhood ?? location?.city}
        </p>
        <h1 className="mt-2 font-display text-5xl">{venue.name}</h1>
        <p className="mt-3 max-w-2xl text-lg text-muted">{venue.description}</p>
        <div className="mt-5 flex flex-wrap gap-4 text-sm">
          {location ? (
            <p>
              {location.address_line1}, {location.city}
            </p>
          ) : null}
          {venue.phone ? <p>{venue.phone}</p> : null}
          {directions ? (
            <a className="text-terracotta underline" href={directions}>
              Directions
            </a>
          ) : null}
        </div>

        <section className="mt-12">
          <h2 className="font-display text-3xl">Happening now</h2>
          {venue.current_deals.length === 0 ? (
            <p className="mt-3 text-muted">Nothing active this minute. Check what’s coming up.</p>
          ) : (
            <div className="mt-5 grid gap-4 md:grid-cols-2">
              {venue.current_deals.map((deal) => (
                <DealCard key={deal.id} deal={deal} />
              ))}
            </div>
          )}
        </section>

        <section className="mt-12">
          <h2 className="font-display text-3xl">Coming up</h2>
          {venue.upcoming_deals.length === 0 ? (
            <p className="mt-3 text-muted">No upcoming specials on the board.</p>
          ) : (
            <div className="mt-5 grid gap-4 md:grid-cols-2">
              {venue.upcoming_deals.map((deal) => (
                <DealCard key={deal.id} deal={deal} />
              ))}
            </div>
          )}
        </section>

        <section className="mt-12 rounded-3xl border border-ink/10 bg-card p-6">
          <h2 className="font-display text-2xl">Why we believe this</h2>
          <p className="mt-2 text-sm text-muted">
            Every published deal keeps a trail back to a source snapshot. This is a placeholder for
            the consumer provenance panel — source type, last verification, and a path to report a
            mistake.
          </p>
          <p className="mt-4 text-sm">
            Sample data is fictional.{" "}
            <Link className="underline" href="/">
              Back to deals
            </Link>
          </p>
        </section>
      </article>
    );
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    throw error;
  }
}
