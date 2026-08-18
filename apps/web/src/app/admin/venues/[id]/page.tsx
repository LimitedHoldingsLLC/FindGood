"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { Pill, freshnessTone, useAdminClient } from "@/features/admin/AdminShell";
import type { AdminRun, AdminVenue } from "@/lib/api/types";

export default function AdminVenueDetailPage() {
  const params = useParams<{ id: string }>();
  const client = useAdminClient();
  const [venue, setVenue] = useState<AdminVenue | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [run, setRun] = useState<AdminRun | null>(null);

  async function load() {
    if (!client) return;
    setVenue(await client.opsVenue(params.id));
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [client, params.id]);

  useEffect(() => {
    if (!client || !run || !["queued", "running"].includes(run.status)) return;
    const timer = setInterval(async () => {
      const next = await client.run(run.id);
      setRun(next);
      if (!["queued", "running"].includes(next.status)) void load();
    }, 3000);
    return () => clearInterval(timer);
  }, [client, run]);

  if (!client || !venue) return <p className="text-sm text-muted">Loading…</p>;

  async function act(label: string, fn: () => Promise<AdminRun | AdminVenue>) {
    setMessage(null);
    const result = await fn();
    if ("job_type" in result) {
      setRun(result);
      setMessage(`${label}: ${result.status}`);
    } else {
      setVenue(result);
      setMessage(label);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs uppercase text-muted">Business</p>
        <h1 className="font-display text-4xl">{venue.name}</h1>
        <p className="text-sm text-muted">
          {venue.address} {venue.city} · {venue.phone}
        </p>
      </div>
      {message ? <p className="text-sm text-forest">{message}</p> : null}
      <div className="flex flex-wrap gap-2">
        <Pill label={venue.freshness_status} tone={freshnessTone(venue.freshness_status)} />
        <Pill label={venue.status} />
      </div>
      <div className="flex flex-wrap gap-2 text-sm">
        <button className="rounded-full bg-ink px-4 py-2 text-paper" onClick={() => act("Crawl queued", () => client.crawlVenue(venue.id))}>
          Crawl website
        </button>
        <button className="rounded-full border border-ink/15 px-4 py-2" onClick={() => act("Google refresh", () => client.refreshGoogle(venue.id))}>
          Refresh Google
        </button>
        <button className="rounded-full border border-ink/15 px-4 py-2" onClick={() => act("Yelp refresh", () => client.refreshYelp(venue.id))}>
          Refresh Yelp
        </button>
        <button
          className="rounded-full border border-ink/15 px-4 py-2"
          onClick={() => act("Tripadvisor refresh", () => client.refreshTripadvisor(venue.id))}
        >
          Refresh Tripadvisor
        </button>
        <button className="rounded-full border border-terracotta/40 px-4 py-2 text-terracotta" onClick={() => act("Disabled", () => client.disableVenue(venue.id))}>
          Disable
        </button>
      </div>
      {run ? (
        <div className="rounded-2xl border border-ink/10 bg-card p-4 text-sm">
          <p>
            Job {run.id.slice(0, 8)} · <Pill label={run.status} /> · pages {run.pages_fetched}/{run.pages_discovered} ·
            offers {run.offers_created}
          </p>
          <Link className="underline" href={`/admin/runs/${run.id}`}>
            Open run
          </Link>
        </div>
      ) : null}
      <section className="rounded-2xl border border-ink/10 bg-card p-5">
        <h2 className="font-medium">Provider IDs</h2>
        <ul className="mt-3 space-y-2 text-sm">
          {venue.provider_links.map((link) => (
            <li key={`${link.provider}-${link.provider_business_id}`}>
              {link.provider}: {link.provider_business_id}{" "}
              {link.provider_url ? (
                <a className="underline" href={link.provider_url} target="_blank" rel="noreferrer">
                  open
                </a>
              ) : null}
            </li>
          ))}
          {venue.provider_links.length === 0 ? <li className="text-muted">No provider links yet.</li> : null}
        </ul>
      </section>
      <section className="rounded-2xl border border-ink/10 bg-card p-5">
        <h2 className="font-medium">Offers</h2>
        <ul className="mt-3 space-y-2 text-sm">
          {venue.offers.map((deal) => (
            <li key={deal.id}>
              <Link className="underline" href={`/admin/deals/${deal.id}`}>
                {deal.title}
              </Link>{" "}
              <Pill label={deal.freshness_status} tone={freshnessTone(deal.freshness_status)} />
            </li>
          ))}
        </ul>
      </section>
      <p className="text-xs text-muted">
        Last seen {venue.last_seen_at ?? "never"} · last verified {venue.last_verified_at ?? "never"} · next refresh{" "}
        {venue.next_refresh_at ?? "not scheduled"}
      </p>
    </div>
  );
}
